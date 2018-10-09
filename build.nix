{ pkgs ? import <nixpkgs> {}, pythonPackages ? "python36Packages" }:

let
  elem = builtins.elem;
  basename = path: with pkgs.lib; last (splitString "/" path);
  startsWith = prefix: full: let
    actualPrefix = builtins.substring 0 (builtins.stringLength prefix) full;
  in actualPrefix == prefix;

  src-filter = path: type: with pkgs.lib;
    let
      ext = last (splitString "." path);
    in
      !elem (basename path) [".git" "__pycache__" ".eggs"] &&
      !elem ext ["egg-info" "pyc"] &&
      !startsWith "result" path;

   basePythonPackages = if builtins.isAttrs pythonPackages
     then pythonPackages
     else builtins.getAttr pythonPackages pkgs;
in
basePythonPackages.buildPythonPackage rec {
  pname = "pymatgen-lammps";
  version = "0.4.5";
  disabled = (!basePythonPackages.isPy3k);

  src = builtins.filterSource src-filter ./.;

  buildInputs = with basePythonPackages; [ pytestrunner ];
  checkInputs = with basePythonPackages; [ pytest pkgs.lammps ];
  propagatedBuildInputs = with basePythonPackages; [ pymatgen ];

  meta = with pkgs; {
    description = "A LAMMPS wrapper using pymatgen";
    homepage = https://gitlab.com/costrouc/pymatgen-lammps;
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ costrouc ];
  };
}
