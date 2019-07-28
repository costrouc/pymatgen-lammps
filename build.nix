{ pkgs ? import <nixpkgs> {}, pythonPackages ? "python3Packages" }:

rec {
  package = pythonPackages.buildPythonPackage rec {
    pname = "pymatgen-lammps";
    version = "master";
    disabled = pythonPackages.isPy27;

    src = builtins.filterSource
        (path: _: !builtins.elem  (builtins.baseNameOf path) [".git" "result" "docs"])
        ./.;

    buildInputs = with pythonPackages; [
      pytestrunner
    ];

    checkInputs = with pythonPackages; [
      pytest
      pkgs.lammps
    ];

    propagatedBuildInputs = with pythonPackages; [
      pymatgen
    ];

    meta = with pkgs.lib; {
      description = "A LAMMPS wrapper using pymatgen";
      homepage = https://github.com/costrouc/pymatgen-lammps;
      license = licenses.mit;
      maintainers = with maintainers; [ costrouc ];
    };
  };

  docker = pkgs.dockerTools.buildLayeredImage {
    name = "pymatgen-lammps";
    tag = "latest";
    contents = [
      (pythonPackages.python.withPackages
        (ps: with ps; [ jupyterlab package ]))
      pkgs.openmpi
      pkgs.lammps
    ];
    config.Cmd = [ "ipython" ];
    maxLayers = 120;
  };
}
