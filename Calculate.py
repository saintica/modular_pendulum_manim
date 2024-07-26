import numpy as np
import scipy

from sympy import symbols 
from sympy.physics import mechanics as mech
from sympy import Dummy, lambdify
from scipy.integrate import odeint
from configparser import ConfigParser

file = 'config.ini'
config = ConfigParser()
config.read(file)

#Parameter Configuration:
n = int(config['PARAMETERS']['n'])                                                       
b = float(config['PARAMETERS']['b'])                                                       
theta = float(config['PARAMETERS']['theta'])
omega = float(config['PARAMETERS']['omega'])
gravity = float(config['PARAMETERS']['gravity'])                                             
duration = int(config['PARAMETERS']['duration'])                                               
fps = int(config['PARAMETERS']['fps'])                                                    
lengths = np.fromstring(config['PARAMETERS']['lengths'], sep = ' ')
masses = np.fromstring(config['PARAMETERS']['masses'], sep = ' ')
trails = config.getboolean('PARAMETERS','trails')
strings = config.getboolean('PARAMETERS','strings')
t = np.linspace(0, duration, duration*fps)



g = symbols('g')
l = symbols('l:{0}'.format(n))
m = symbols('m:{0}'.format(n))
q = mech.dynamicsymbols('q:{0}'.format(n))
u = mech.dynamicsymbols('u:{0}'.format(n))

#Returns Equations of Motion
def kanes_method(n):
    
    particles, forces, kde = ([] for i in range(3))

    t = symbols('t')
    N = mech.ReferenceFrame('N')
    O = mech.Point('O')
    O.set_vel(N,0)

    for i in range(n):
        
        Ni = N.orientnew('N' + str(i), 'Axis', [q[i], N.z])      
        
        PL = O.locatenew('PL' + str(i), l[i] * Ni.y)                   
        
        PO = mech.Particle('PO' + str(i), PL, m[i])             
        particles.append(PO)
        
        forces.append((PL, (g*m[i]*N.y) + (b*u[i]*N.x + b*u[i]*N.y + b*u[i]*N.z)))
        kde.append(q[i].diff(t) - u[i])
        
        O = PL #Sets the reference frame as the current one for the next iteration
        
    KM = mech.KanesMethod(N, q, u, kd_eqs = kde)
    fr, fr_star = KM.kanes_equations(particles, forces)

    return KM, fr, fr_star

#Returns the X-Y coordinates [Xi,Yi]
def integrate(n, KM, times, initial_thetas, initial_omegas = 0):
    
    y0 = np.deg2rad(np.concatenate([np.broadcast_to(initial_thetas, n), np.broadcast_to(initial_omegas, n)]))
    
    parameters = [g] + list(l) + list(m)
    parameter_vals = [gravity] + list(lengths) + list(masses)
    
    unknowns = [Dummy() for i in q + u]
    unknown_dict = dict(zip(q + u, unknowns))
    kds = KM.kindiffdict()
    
    mm_sym = KM.mass_matrix_full.subs(kds).subs(unknown_dict)
    fo_sym = KM.forcing_full.subs(kds).subs(unknown_dict)
    
    mm_num = lambdify(unknowns + parameters, mm_sym)
    fo_num = lambdify(unknowns + parameters, fo_sym)
    
    #Returns Generalized Coordiantes and Velocities [qi,ui]
    def solve_matrix(y, t, args):
        nums = list(y) + list(args)
        sol = np.linalg.solve(mm_num(*nums), fo_num(*nums))
        return np.array(sol).T[0]
    
    #Returns the X-Y coordinates [Xi,Yi]
    def get_xy_coords(gen_coords):
        x = lengths * np.sin(gen_coords[:, :n])
        y = -lengths * np.cos(gen_coords[:, :n])
        return np.cumsum(x, 1), np.cumsum(y, 1)
    
    generalized_coords = scipy.integrate.odeint(solve_matrix, y0, times, args = (parameter_vals,))
    x, y = get_xy_coords(generalized_coords)
    return(x, y)


KM, fr, fr_star = kanes_method(n)
x, y = integrate(n, KM, t, theta)
