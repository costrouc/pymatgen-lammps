{ pkgs ? import <nixpkgs> { } }:

let build = import ./build.nix {
      inherit pkgs;
      pythonPackages = pkgs.python3Packages;
    };
in {
  pymatgen-lammps = build.package;
  pymatgen-lammps-docker = build.docker;
}
