from collections import Counter
from scipy.stats import norm
import matplotlib.pyplot as plt
from pymatgen.util.plotting_utils import get_publication_quality_plot
from scipy import stats
import numpy as np


class RadialDistributionFunction(object):
    """
    Calculate the average radial distribution function for a given set of structures.
    """

    def __init__(self, structures, ngrid=101, rmax=10.0, cellrange=1, sigma=0.1,
                 species=None, reference_species=None):
        """
        Args:
            structures (list of pmg_structure objects): List of structure
                objects with the same composition. Allow for ensemble averaging.
            ngrid (int): Number of radial grid points.
            rmax (float): Maximum of radial grid (the minimum is always set zero).
            cellrange (int): Range of translational vector elements associated
                with supercell. Default is 1, i.e. including the adjecent image
                cells along all three directions.
            sigma (float): Smearing of a Gaussian function.
            species ([string]): A list of specie symbols of interest.
            reference_species ([string]): set this option along with 'species'
                parameter to compute pair radial distribution function.
                eg: species=["H"], reference_species=["O"] to compute
                    O-H pair distribution in a water MD simulation.
        """

        if ngrid < 1:
            raise ValueError("ngrid should be greater than 1")

        if sigma <= 0.0:
            raise ValueError("sigma should be > 0")

        lattice = structures[0].lattice
        indices = [j for j, site in enumerate(structures[0]) if site.specie.symbol in species]

        if len(indices) == 0:
            raise ValueError("Given species are not in the structure")

        ref_indices = indices
        if reference_species:
            ref_indices = [j for j, site in enumerate(structures[0])
                           if site.specie.symbol in reference_species]

        self.rho = float(len(indices)) / lattice.volume
        fcoords_list = []
        ref_fcoords_list = []

        for s in structures:
            all_fcoords = np.array(s.frac_coords)
            fcoords_list.append(all_fcoords[indices, :])
            ref_fcoords_list.append(all_fcoords[ref_indices, :])

        dr = rmax / (ngrid - 1)
        interval = np.linspace(0.0, rmax, ngrid)
        rdf = np.zeros((ngrid), dtype=np.double)
        dns = Counter()

        # generate the translational vectors
        r = np.arange(-cellrange, cellrange + 1)
        arange = r[:, None] * np.array([1, 0, 0])[None, :]
        brange = r[:, None] * np.array([0, 1, 0])[None, :]
        crange = r[:, None] * np.array([0, 0, 1])[None, :]
        images = arange[:, None, None] + brange[None, :, None] + crange[None, None, :]
        images = images.reshape((len(r) ** 3, 3))

        # find the zero image vector
        zd = np.sum(images ** 2, axis=1)
        indx0 = np.argmin(zd)

        for fcoords, ref_fcoords in zip(fcoords_list, ref_fcoords_list):
            dcf = fcoords[:, None, None, :] + images[None, None, :,
                                              :] - ref_fcoords[None, :, None, :]
            dcc = lattice.get_cartesian_coords(dcf)
            d2 = np.sum(dcc ** 2, axis=3)
            dists = [d2[u, v, j] ** 0.5 for u in range(len(indices)) for v in
                     range(len(ref_indices))
                     for j in range(len(r) ** 3) if u != v or j != indx0]
            dists = filter(lambda e: e < rmax + 1e-8, dists)
            r_indices = [int(dist / dr) for dist in dists]
            dns.update(r_indices)

        for indx, dn in dns.most_common(ngrid):
            if indx > len(interval) - 1: continue

            if indx == 0:
                ff = np.pi * dr ** 2
            else:
                ff = 4.0 * np.pi * interval[indx] ** 2

            rdf[:] += stats.norm.pdf(interval, interval[indx], sigma) * dn \
                      / float(len(ref_indices)) / ff / self.rho / len(
                fcoords_list)

        self.structures = structures
        self.rdf = rdf
        self.interval = interval
        self.cellrange = cellrange
        self.rmax = rmax
        self.ngrid = ngrid
        self.species = species
        self.dr = dr

    @property
    def coordination_number(self):
        """
        returns running coordination number

        Returns:
            numpy array
        """
        return np.cumsum(self.rdf * self.rho * 4.0 * np.pi * self.interval ** 2)

    def get_rdf_plot(self, label=None, xlim=[0.0, 8.0], ylim=[-0.005, 3.0]):
        """
        Plot the average RDF function.
        """

        if label is None:
            symbol_list = [e.symbol for e in
                           self.structures[0].composition.keys()]
            symbol_list = [symbol for symbol in symbol_list if
                           symbol in self.species]

            if len(symbol_list) == 1:
                label = symbol_list[0]
            else:
                label = "-".join(symbol_list)

        plt = get_publication_quality_plot(12, 8)
        plt.plot(self.interval, self.rdf, color="r", label=label, linewidth=4.0)
        plt.xlabel("$r$ ($\AA$)")
        plt.ylabel("$g(r)$")
        plt.legend(loc='upper right', fontsize=36)
        plt.xlim(xlim[0], xlim[1])
        plt.ylim(ylim[0], ylim[1])
        plt.tight_layout()

        return plt

    def export_rdf(self, filename):
        """
        Output RDF data to a csv file.

        Args:
            filename (str): Filename. Supported formats are csv and dat. If
                the extension is csv, a csv file is written. Otherwise,
                a dat format is assumed.
        """
        fmt = "csv" if filename.lower().endswith(".csv") else "dat"
        delimiter = ", " if fmt == "csv" else " "
        with open(filename, "wt") as f:
            if fmt == "dat":
                f.write("# ")
            f.write(delimiter.join(["r", "g(r)"]))
            f.write("\n")

            for r, gr in zip(self.interval, self.rdf):
                f.write(delimiter.join(["%s" % v for v in [r, gr]]))
                f.write("\n")
