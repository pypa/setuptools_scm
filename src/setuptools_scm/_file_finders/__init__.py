from __future__ import annotations

import itertools
import os
from typing import Callable
from typing import TYPE_CHECKING

from .. import _log
from .. import _types as _t
from .._entrypoints import iter_entry_points

if TYPE_CHECKING:
    from typing_extensions import TypeGuard


log = _log.log.getChild("file_finder")


def scm_find_files(
    path: _t.PathT,
    scm_files: set[str],
    scm_dirs: set[str],
    force_all_files: bool = False,
) -> list[str]:
    """ setuptools compatible file finder that follows symlinks

    - path: the root directory from which to search
    - scm_files: set of scm controlled files and symlinks
      (including symlinks to directories)
    - scm_dirs: set of scm controlled directories
      (including directories containing no scm controlled files)
    - force_all_files: ignore ``scm_files`` and ``scm_dirs`` and list everything.

    scm_files and scm_dirs must be absolute with symlinks resolved (realpath),
    with normalized case (normcase)

    Spec here: http://setuptools.readthedocs.io/en/latest/setuptools.html#\
        adding-support-for-revision-control-systems
    """
    realpath = os.path.normcase(os.path.realpath(path))
    seen: set[str] = set()
    res: list[str] = []
    for dirpath, dirnames, filenames in os.walk(realpath, followlinks=True):
        # dirpath with symlinks resolved
        realdirpath = os.path.normcase(os.path.realpath(dirpath))

        def _link_not_in_scm(n: str) -> bool:
            fn = os.path.join(realdirpath, os.path.normcase(n))
            return os.path.islink(fn) and fn not in scm_files

        if not force_all_files and realdirpath not in scm_dirs:
            # directory not in scm, don't walk it's content
            dirnames[:] = []
            continue
        if os.path.islink(dirpath) and not os.path.relpath(
            realdirpath, realpath
        ).startswith(os.pardir):
            # a symlink to a directory not outside path:
            # we keep it in the result and don't walk its content
            res.append(os.path.join(path, os.path.relpath(dirpath, path)))
            dirnames[:] = []
            continue
        if realdirpath in seen:
            # symlink loop protection
            dirnames[:] = []
            continue
        dirnames[:] = [
            dn for dn in dirnames if force_all_files or not _link_not_in_scm(dn)
        ]
        for filename in filenames:
            if not force_all_files and _link_not_in_scm(filename):
                continue
            if not force_all_files and filename.lower().endswith(".ipynb"):
                # ignore jupyter notebooks by default.
                # they can be included with a MANIFEST.in
                # 1) jupyter notebooks are ubiquitous in python repositories,
                # they are saved in git and detected by setuptools-scm.
                # 2) it's common for a notebook file to reach dozens
                # or hundreds of MB (jupyter saves the content of each cell on save).
                # 3) there is no expectation of these files to be included in
                # or distributed via the python wheel.
                continue
            # dirpath + filename with symlinks preserved
            fullfilename = os.path.join(dirpath, filename)
            is_tracked = os.path.normcase(os.path.realpath(fullfilename)) in scm_files
            if force_all_files or is_tracked:
                res.append(os.path.join(path, os.path.relpath(fullfilename, realpath)))
        seen.add(realdirpath)
    return res


def is_toplevel_acceptable(toplevel: str | None) -> TypeGuard[str]:
    """ """
    if toplevel is None:
        return False

    ignored: list[str] = os.environ.get("SETUPTOOLS_SCM_IGNORE_VCS_ROOTS", "").split(
        os.pathsep
    )
    ignored = [os.path.normcase(p) for p in ignored]

    log.debug("toplevel: %r\n    ignored %s", toplevel, ignored)

    return toplevel not in ignored


def find_files(path: _t.PathT = "") -> list[str]:
    for ep in itertools.chain(
        iter_entry_points("setuptools_scm.files_command"),
        iter_entry_points("setuptools_scm.files_command_fallback"),
    ):
        command: Callable[[_t.PathT], list[str]] = ep.load()
        res: list[str] = command(path)
        if res:
            return res
    return []
