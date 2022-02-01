"""
:copyright: 2010-2015 by Ronny Pfannschmidt
:license: MIT
"""
import os
import warnings
from typing import Optional
from typing import TYPE_CHECKING

from . import _types
from ._entrypoints import _call_entrypoint_fn
from ._entrypoints import _version_from_entrypoints
from ._overrides import _read_pretended_version_for
from ._overrides import PRETEND_KEY
from ._overrides import PRETEND_KEY_NAMED
from ._version_cls import _version_as_tuple
from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .config import Configuration
from .config import DEFAULT_LOCAL_SCHEME
from .config import DEFAULT_TAG_REGEX
from .config import DEFAULT_VERSION_SCHEME
from .discover import iter_matching_entrypoints
from .utils import function_has_arg
from .utils import trace
from .version import format_version
from .version import meta
from .version import ScmVersion

if TYPE_CHECKING:
    from typing import NoReturn


TEMPLATES = {
    ".py": """\
# coding: utf-8
# fmt: off
# file generated by setuptools_scm
# don't change, don't track in version control
version = {version!r}
version_tuple = {version_tuple!r}
""",
    ".txt": "{version}",
}


def version_from_scm(root):
    warnings.warn(
        "version_from_scm is deprecated please use get_version",
        category=DeprecationWarning,
        stacklevel=2,
    )
    config = Configuration(root=root)
    return _version_from_entrypoints(config)


def dump_version(
    root: _types.PathT,
    version: str,
    write_to: _types.PathT,
    template: "str | None" = None,
):
    assert isinstance(version, str)
    target = os.path.normpath(os.path.join(root, write_to))
    ext = os.path.splitext(target)[1]
    template = template or TEMPLATES.get(ext)

    if template is None:
        raise ValueError(
            "bad file format: '{}' (of {}) \nonly *.txt and *.py are supported".format(
                os.path.splitext(target)[1], target
            )
        )
    version_tuple = _version_as_tuple(version)

    with open(target, "w") as fp:
        fp.write(template.format(version=version, version_tuple=version_tuple))


def _do_parse(config: Configuration) -> "ScmVersion|None":
    pretended = _read_pretended_version_for(config)
    if pretended is not None:
        return pretended

    if config.parse:
        parse_result = _call_entrypoint_fn(config.absolute_root, config, config.parse)
        if isinstance(parse_result, str):
            raise TypeError(
                "version parse result was a string\nplease return a parsed version"
            )
        version: Optional[ScmVersion]
        if parse_result:
            assert isinstance(parse_result, ScmVersion)
            version = parse_result
        else:
            version = _version_from_entrypoints(config, fallback=True)
    else:
        # include fallbacks after dropping them from the main entrypoint
        version = _version_from_entrypoints(config) or _version_from_entrypoints(
            config, fallback=True
        )

    return version


def _version_missing(config) -> "NoReturn":
    raise LookupError(
        f"setuptools-scm was unable to detect version for {config.absolute_root}.\n\n"
        "Make sure you're either building from a fully intact git repository "
        "or PyPI tarballs. Most other sources (such as GitHub's tarballs, a "
        "git checkout without the .git folder) don't contain the necessary "
        "metadata and will not work.\n\n"
        "For example, if you're using pip, instead of "
        "https://github.com/user/proj/archive/master.zip "
        "use git+https://github.com/user/proj.git#egg=proj"
    )


def get_version(
    root=".",
    version_scheme=DEFAULT_VERSION_SCHEME,
    local_scheme=DEFAULT_LOCAL_SCHEME,
    write_to=None,
    write_to_template=None,
    relative_to=None,
    tag_regex=DEFAULT_TAG_REGEX,
    parentdir_prefix_version=None,
    fallback_version=None,
    fallback_root=".",
    parse=None,
    git_describe_command=None,
    dist_name=None,
    version_cls=None,
    normalize=True,
    search_parent_directories=False,
):
    """
    If supplied, relative_to should be a file from which root may
    be resolved. Typically called by a script or module that is not
    in the root of the repository to direct setuptools_scm to the
    root of the repository by supplying ``__file__``.
    """

    config = Configuration(**locals())
    maybe_version = _get_version(config)
    if maybe_version is None:
        _version_missing(config)
    return maybe_version


def _get_version(config: Configuration) -> "str|None":
    parsed_version = _do_parse(config)
    if parsed_version is None:
        return None
    version_string = format_version(
        parsed_version,
        version_scheme=config.version_scheme,
        local_scheme=config.local_scheme,
    )
    if config.write_to is not None:
        dump_version(
            root=config.root,
            version=version_string,
            write_to=config.write_to,
            template=config.write_to_template,
        )

    return version_string


# Public API
__all__ = [
    "get_version",
    "dump_version",
    "version_from_scm",
    "Configuration",
    "DEFAULT_VERSION_SCHEME",
    "DEFAULT_LOCAL_SCHEME",
    "DEFAULT_TAG_REGEX",
    "PRETEND_KEY",
    "PRETEND_KEY_NAMED",
    "Version",
    "NonNormalizedVersion",
    # TODO: are the symbols below part of public API ?
    "function_has_arg",
    "trace",
    "format_version",
    "meta",
    "iter_matching_entrypoints",
]
