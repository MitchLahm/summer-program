import psi4
import numpy as np
import configparser
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm
import abc


class SCF:
    """
    A stub SCF class to be used for RHF, UHF, etc.
    """
    def __init__(self, options_ini):
        self.config = configparser.ConfigParser()
        self.config.read(options_ini)
        self.molecule = psi4.geometry(self.config['DEFAULT']['molecule'])
        self.molecule.update_geometry()
        self.V_nuc = self.molecule.nuclear_repulsion_energy()

        self.options = {}
        self.options['BASIS'] = self.config['DEFAULT']['basis']
        self.options['SCF_MAX_ITER'] = self.config.getint('SCF', 'max_iter', fallback=50)

        self.options['DIIS'] = self.config.getboolean('SCF', 'diis', fallback=True)
        self.options['DIIS_NVECTOR'] = self.config.getint('SCF', 'diis_nvector', fallback=6)
        self.options['DIIS_START'] = self.config.getint('SCF', 'diis_start', fallback=6)

        self.basis = psi4.core.BasisSet.build(self.molecule, 'BASIS', self.options['BASIS'], puream=0)
        self.mints = psi4.core.MintsHelper(self.basis)

        self.S = self.mints.ao_overlap().to_array()
        self.T = self.mints.ao_kinetic().to_array()
        self.V = self.mints.ao_potential().to_array()
        self.g = self.mints.ao_eri().to_array()

        self.H = self.T + self.V

        A = self.mints.ao_overlap()
        A.power(-0.5, 1.e-16)
        self.A = A.to_array()

        self.spin = 0

    @abc.abstractmethod
    def energy(self):
        """
        Compute the SCF energy
        """
        return

    def extrapolate_diis(self):
        """
        Extrapolate the Fock matrix
        :yield: Fock matrices that need to be extrapolated
        P. Pulay, Chem. Phys. Lett. 73, 393 (1980).

        e = F*D*S - S*D*F
        P*q = f
        +---+---+---+---+ +---+   +---+
        |P00|P01|P02|-1 | | q0|   | 0 |
        +---+---+---+---+ +---+   +---+
        |P10|P11|P12|-1 | | q1|   | 0 |
        +---+---+---+---+ +---+ = +---+
        |P20|P21|P22|-1 | | q2|   | 0 |
        +---+---+---+---+ +---+   +---+
        |-1 |-1 |-1 | 0 | | λ |   |-1 |
        +---+---+---+---+ +---+   +---+
        """
        S = self.S
        start = max(1, len(self.focks) - self.options['DIIS_NVECTOR'])
        focks, densities = self.focks[start:], self.densities[start:]

        num_mats = len(focks)
        if isinstance(focks[0], (list, tuple)):
            e_vecs = []
            for (Fa, Fb), (Da, Db) in zip(focks, densities):
                e_a = Fa @ Da @ S - S @ Da @ Fa
                e_b = Fb @ Db @ S - S @ Db @ Fb
                e_vecs.append(np.append(e_a, e_b, axis=0))
        else:
            e_vecs = [F @ D @ S - S @ D @ F for F, D in zip(focks, densities)]

        P = np.zeros((num_mats + 1, num_mats + 1))
        for i, j in zip(*np.triu_indices(num_mats)):
            P[i, j] = P[j, i] = (e_vecs[i]*e_vecs[j]).sum()
        P[-1,  :] = P[ :, -1] = -1

        f = np.zeros((num_mats + 1))
        f[-1] = -1

        q_vec = np.linalg.solve(P, f)

        if isinstance(focks[0], (list, tuple)):
            focks = [(q*Fa, q*Fb) for q, (Fa, Fb) in zip(q_vec[:-1], focks)]
            return np.array(focks).sum(axis=0)
        else:
            return sum([q*F for q, F in zip(q_vec[:-1], focks)])

    @property
    def spin_contamination(self):
        """
        Compute the spin contamination
        """
        spin, na, nb, Ca, Cb, S = self.spin, self.n_occ_a, self.n_occ_b, self.Ca, self.Cb, self.S

        # Catch spin-restricted case (Ca and Cb would be undefined)
        if spin == 0:
            return 0

        s2_expected = spin*(spin+1)

        X = Ca.T @ S @ Cb
        dN = np.vdot(X, X)
        ΔS = min(na, nb) - dN
        s2_observed = s2_expected + ΔS
        print("dN: {}  ΔS: {}".format(round(dN, 10), ΔS))
        print("S^2 expected:", s2_expected)
        print("S^2 observed:", s2_observed)

        return s2_observed

    def plot_convergence(self):
        """
        Plot the convergence of energy change and density norm
        """
        energies, d_norms = np.array(self.energies), self.d_norms
        plt.plot(abs(energies[1:-1] - energies[2:]), label=r'$\Delta$ E')
        plt.plot(d_norms[1:], label=r'$||\Delta$ D$||$')
        plt.yscale('log')
        plt.legend()
        plt.show()

    def plot_densities(self):
        """
        Plot the densities
        """
        densities = self.densities
        fig, axes = plt.subplots(3, 3)
        axes = axes.reshape(-1)
        cmap = plt.get_cmap('Oranges_r')

        for i in range(1, min(len(densities), 10)):
            # Select distributed throughout
            j = i
            d = densities[j]
            if len(densities) > 10:
                j = len(densities)//10 * i
                d = densities[j]
            ax = axes[i - 1]
            ax.set_title('{:d}'.format(j))
            ax.imshow(d, interpolation='nearest', cmap=cmap, norm=LogNorm(vmin=1.0e-10, vmax=d.max()))

        fig.colorbar(densities[-1])
        plt.show()


    def plot_density_changes(self):
        """
        Plot the change in density
        """
        densities = self.densities
        fig, axes = plt.subplots(3, 3)
        axes = axes.reshape(-1)
        cmap = plt.get_cmap('Oranges_r')

        ims = []
        for i in range(1, min(len(densities), 10)):
            # Select distributed throughout
            j = i
            d_change = densities[j] - densities[j-1]
            if len(densities) > 10:
                j = len(densities)//10 * i
                d = densities[j] - densities[j-1]
            ax = axes[i - 1]
            ax.set_title('{:d}'.format(j))
            ims.append(ax.imshow(d, interpolation='nearest', cmap=cmap, norm=LogNorm(vmin=1.0e-10, vmax=d.max())))

        fig.colorbar(ims[-1])
        plt.show()

    def plot_focks(self):
        """
        Plot the focks
        """
        focks = self.focks
        fig, axes = plt.subplots(3, 3)
        axes = axes.reshape(-1)
        cmap = plt.get_cmap('Oranges_r')

        for i in range(1, min(len(focks), 10)):
            # Select distributed throughout
            j = i
            f = focks[j]
            if len(focks) > 10:
                j = len(focks)//10 * i
                f = focks[j]
            ax = axes[i - 1]
            ax.set_title('{:d}'.format(j))
            ax.imshow(f, interpolation='nearest', cmap=cmap, norm=LogNorm(vmin=1.0e-10, vmax=f.max()))

        fig.colorbar(focks[-1])
        plt.show()
