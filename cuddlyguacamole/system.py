import numpy as np
import lennardjones
import neighbourlist
import copy
import pbc
import metropolis

############################################################################
# Define Particle and Box classes 
############################################################################
class Particle(object):
    """A particle. Particles have the following properties:

    Attributes:
        position: a one to three dimensional position vector of numpy.array type
        charge (float): charge of the particle
        self.sigmaLJ (float): distance at which LJ potential is 0 for particle type
        self.epsilonLJ (float): depth of LJ potential well for particle type
        neighbourlist (array like of Particle): a list of of neighbours of the particle
        (verlet neighbourlist of particles within cutoff+skin radius) 
    """

    def __init__(self, position, charge, sigmaLJ = 1.0, epsilonLJ = 1.0):
        """Return a Particle object whose position is *position*,
        electric charge is *charge*, sigma and epsilon for the Leonard-Jones
        potential is *sigmaLJ* and *epsilonLJ*, and neighbourlist is *neighbourlist*"""
        self.position = position
        self.charge = charge
        self.sigmaLJ = sigmaLJ
        self.epsilonLJ = epsilonLJ
        self.neighbourlist = None


class Box(object):
    """A 1 to 3-dimensional square box in space, containing charged particles:

    Attributes:
        dimension (int): dimension of the box (1-3)
        size (*dimension*-dimensional numpy array of float): 1d-3d numpy array giving size of the box in each direction
        center (*dimension*-dimensional numpy array of loat): 1d-3d numpy array locating the center of the box (always the origin)
        particles (list of Particle): list of particles in the box
        positions (python list of *dimension*-dimensional numpy arrays with the position of all the particles, for ease of use... only
                create if needed using a set method? and always store if created?)
                region (*dimension*x2-dimensional numpy array of float): specifies the region
                in space that the box covers (automatically computed from the center and the size of the box?)
        LJpotential (float): Lennard Jones Potential of the system (calculated based on the positions of the particles in *particles*)
        temp (float): temperature in the box
        ????LJneighbourlist (list of numpy arrays of int): a list with of same size as *particles*,
                                                     with a numpy array of int for each particle listing the indices of the 
                                                     neighbouring particles (particles within the LJ cutoff radius)
        r_c_LJ (float): cutoff radius for LJ potential calculation
        r_skin_LJ (float): size of skin region for LJ potential calculation 
    """

    def __init__(self, dimension, size, particles, temp, optimisation_pos_history=[], optimisation_pot_history = []):
        """Return a Box object of dimension *dimension* (between 1 and 3),
        whose length(&breadth&height) is *size*, is centered at *center*, 
        and contains the particles in the numpy array *particles*"""
        
        self.dimension = dimension
        self.size = size
        self.center = np.zeros(dimension)
        self.particles = particles
        self.LJpotential = None
        self.temp = temp
        self.Cpotential = None
        self.pos_history = None
        self.pot_history = None
        self.optimisation_pos_history = optimisation_pos_history # variable to keep all position histories throughout the optimisation
        self.optimisation_pot_history = optimisation_pot_history

        for particle in particles:
            particle.position = pbc.enforce_pbc(particle.position, size)
        self.make_positions_list()

    def compute_LJneighbourlist(self, r_cut, r_skin):
        self.particles = neighbourlist.verlet_neighbourlist(self.particles, r_cut, r_skin)

    def compute_LJ_potential(self, r_cut, r_skin):
        self.LJpotential = lennardjones.LJ_potential(self.particles, r_cut, r_skin)

    def make_positions_list(self): # update positions list based on position registered to each particle in particles
        self.positions = [] 
        for particle in self.particles:
            self.positions.append(particle.position)

    def update_particle_positions(self): # update registered position for each particle based on positions list
        for i in range(len(self.particles)):
            self.particles[i].position = self.positions[i]

    def compute_energy(self, r_cutLJ, r_skinLJ, r_cutCo, r_skinCo):
        self.compute_LJ_potential(r_cutLJ, r_skinLJ)
        self.compute_Coloumb_potential(r_cutCo, r_skinCo)

    def compute_Coloumb_potential(self, r_cutCo, r_rkin_Co):
        self.Cpotential = 0

    def simulate(self, n_steps, n_reuse_nblist, n_skip, width, save_system_history, r_cut_LJ, r_skin_LJ, r_cut_Co = 0, r_skin_Co = 0):
        self.positions, self.LJpotential, self.pos_history, self.pot_history, _ = metropolis.mcmc(self, n_steps, width, n_skip, n_reuse_nblist, save_system_history, r_cut_LJ, r_skin_LJ)
        self.update_particle_positions()
        self.compute_LJneighbourlist(r_cut_LJ, r_skin_LJ)

    def optimize(self, n_opt, tol_opt, n_steps, n_reuse_nblist, n_skip, width, save_system_history, r_cut_LJ, r_skin_LJ, r_cut_Co = 0, r_skin_Co = 0):
        original_temp = self.temp # store original box temperature

        temp_decrease_factors = 1.0/(np.ones(n_opt)*range(1, n_opt+1)) # reduce temperature on each simulation i by temp_decrease_factors[i]
        temperatures = self.temp * np.ones(n_opt) * temp_decrease_factors
        
        i=0
        # positions_tmp = [np.ones(self.dimension) for x in range(len(self.positions))]
        # positions_tmp[0] = 1e15*np.ones(self.dimension) # give positions_tmp[0] some large arbitrary value to pass the first while check
        # while np.linalg.norm(np.asarray(self.positions) - np.asarray(positions_tmp)) > tol_opt and i < n_opt:
        LJpotential_old = 1e16
        while np.abs((self.LJpotential - LJpotential_old)/self.LJpotential) > tol_opt and i < n_opt:
            # positions_tmp = self.positions
            LJpotential_old = self.LJpotential
            self.temp = temperatures[i]
            self.simulate(n_steps, n_reuse_nblist, n_skip, width, save_system_history, r_cut_LJ, r_skin_LJ)
            
            print(np.abs((self.LJpotential - LJpotential_old)/self.LJpotential))
            i += 1
            self.optimisation_pos_history.append(list(self.pos_history)) # store all position histories
            self.optimisation_pot_history.append(list(self.pot_history))

        self.temp = original_temp # reset temperature
        
        



