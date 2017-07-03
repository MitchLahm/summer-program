import psi4
import numpy as np
import sys
sys.path.insert(0, '../../4/jevandezande')
from mp2 import MP2


class UMP2(MP2):
    """
    Spinorbital version of MP2 (i.e. MP2 using an unrestricted reference)
    """

    def __init__(self, uhf, df_basis_name=''):
        super().__init__(uhf, df_basis_name)

        # Antisymmetrize gmo
        self.gmo = self.gmo.transpose(0, 2, 1, 3) - self.gmo.transpose(0, 2, 3, 1)

    def energy(self):
        """
        Compute the UMP2 energy
        :return: UMP2 energy
        """
        nocc, gmo, e = self.nocc, self.gmo, self.e

        Ec = 0.0
        for i in range(nocc):
            for j in range(nocc):
                for a in range(nocc, len(e)):
                    for b in range(nocc, len(e)):
                        Ec += (1/4.0) * gmo[i, j, a, b]**2 / (e[i]+e[j]-e[a]-e[b])

        self.Ec = Ec
        self.E_mp2 = Ec + self.E_scf

        df = 'DF-' if self.df_basis_name else ''
        print('@{}MP2 correlation energy: {:15.10f}\n'.format(df, self.Ec))
        print('@{}Total MP2 energy: {:15.10f}\n'.format(df, self.E_mp2))

        return self.E_mp2


if __name__ == "__main__":
    sys.path.insert(0, '../../3/jevandezande')
    from uhf import UHF
    uhf = UHF('../../3/jevandezande/Options.ini')
    uhf.energy()

    ump2 = UMP2(uhf)
    e = ump2.energy()

    dfump2 = UMP2(uhf, 'cc-pVDZ-RI')
    df_e = dfump2.energy()

    print("Energy Error: {:7.5e}".format(df_e - e))
    print("norm(UMP2.gmo - DFUMP2.gmo): {:7.5E}".format(np.linalg.norm(ump2.gmo - dfump2.gmo)))
