"""
Common JS/CSS includes for Sahana Eden.

Provides helper functions to inject CSS and JS resources during
page rendering. All logic is kept compatible with the original
Sahana framework; no functional behaviour is changed.

Refactored for:
    - Improved readability
    - Reduced code duplication
    - Clearer helper abstractions
    - Consistent naming and comments

Support Interface Maintenance:
    - Evaluative Maintenance: Developer diagnostics via _log_debug()
    - Consultative Maintenance: Documentation explaining system design
    - Training Maintenance: Developer notes for onboarding contributors
"""

import os
from gluon import current, HTTP, URL, XML


# =============================================================================
# Module Overview (Consultative Maintenance)
# =============================================================================
#
# This module controls how Sahana Eden loads CSS and JS resources.
# It impacts almost every UI screen due to dependencies on:
#   - theme css.cfg files
#   - sahana.js.cfg script bundles
#   - DataTables, ExtJS, and Underscore.js
#
# Developers modifying UI behaviour will frequently interact with:
#   include_debug_css()
#   include_debug_js()
#   include_datatable_js()
#   include_ext_js()
#   include_underscore_js()
#
# This high-level explanation helps new contributors understand the
# purpose and expected behaviour of this module.
#
# =============================================================================


# =============================================================================
# Developer Diagnostics (Evaluative Maintenance)
# =============================================================================

def _log_debug(message):
    """
    Lightweight internal logging helper.

    This function supports Evaluative Maintenance by helping developers
    trace module behaviour without affecting runtime functionality.

    Args:
        message (str): Message to print to the developer log.
    """
    if hasattr(current, "log"):
        current.log.debug(f"[includes.py] {message}")


# =============================================================================
# Helper Functions
# =============================================================================

def _abs_theme_config_path(request, theme):
    """
    Compute absolute path to the active theme's css.cfg file.

    Args:
        request: web2py request object
        theme: name of the active theme folder

    Returns:
        Absolute path to modules/templates/<theme>/css.cfg
    """
    return os.path.join(request.folder, "modules", "templates", theme, "css.cfg")


def _stylesheet_link_tag(appname, css_file):
    """
    Build an HTML <link> tag pointing to static/styles/<css_file>.

    Args:
        appname: current web2py app name
        css_file: relative path under static/styles

    Returns:
        HTML <link> tag as a string
    """
    return (
        f'<link href="/{appname}/static/styles/{css_file}" '
        f'rel="stylesheet" type="text/css" />'
    )


def _append_script(scripts, appname, script_path):
    """
    Append a script from static/scripts into s3.scripts.

    Args:
        scripts: s3.scripts list
        appname: current app name
        script_path: relative path under static/scripts
    """
    scripts.append(f"/{appname}/static/scripts/{script_path}")


# =============================================================================
# CSS Includes
# =============================================================================

def include_debug_css():
    """
    Include all CSS listed in the active theme's css.cfg file.

    css.cfg lives under:
        modules/templates/<theme>/css.cfg

    Non-comment lines represent paths under static/styles/.
    """

    request = current.request
    response = current.response

    theme = response.s3.theme_config
    cfg_path = _abs_theme_config_path(request, theme)

    if not os.path.isfile(cfg_path):
        raise HTTP(
            500,
            f"Missing theme CSS config: modules/templates/{theme}/css.cfg",
        )

    app = request.application
    links = []
    css_entries = []

    with open(cfg_path, "r") as cfg:
        for line in cfg:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            css_entries.append(line)

    _log_debug(f"Loaded CSS entries from {cfg_path}: {css_entries}")

    # Build HTML link tags
    for entry in css_entries:
        links.append(_stylesheet_link_tag(app, entry))

    return XML("\n".join(links))


# =============================================================================
# JavaScript Includes (Debug Mode)
# =============================================================================

def include_debug_js():
    """
    Include JS scripts listed in static/scripts/tools/sahana.js.cfg.

    mergejsmf.getFiles resolves dependency ordering automatically.
    """

    request = current.request
    scripts_dir = os.path.join(request.folder, "static", "scripts")

    import mergejsmf

    config_map = {
        ".": scripts_dir,
        "ui": scripts_dir,
        "web2py": scripts_dir,
        "S3": scripts_dir,
    }

    cfg_file = os.path.join(scripts_dir, "tools", "sahana.js.cfg")

    _, file_list = mergejsmf.getFiles(config_map, cfg_file)

    _log_debug(f"JS loading order: {file_list}")

    app = request.application
    template = f'<script src="/{app}/static/scripts/%s"></script>'

    return XML("\n".join(template % path for path in file_list))


# =============================================================================
# DataTables Includes
# =============================================================================

def include_datatable_js():
    """
    Include required DataTables JS files based on:
        - s3.debug (debug or minified)
        - s3.datatable_opts (responsive, variable_columns)
    """

    s3 = current.response.s3
    scripts = s3.scripts
    options = s3.datatable_opts or {}
    debug = s3.debug
    app = current.request.application

    def add(script):
        _append_script(scripts, app, script)

    # Base DataTables
    add("jquery.dataTables.js" if debug else "jquery.dataTables.min.js")

    # Optional features
    if options.get("responsive"):
        add("jquery.dataTables.responsive.js" if debug else "jquery.dataTables.responsive.min.js")

    if options.get("variable_columns"):
        add("S3/s3.ui.columns.js" if debug else "S3/s3.ui.columns.min.js")

    # Eden wrapper
    add("S3/s3.ui.datatable.js" if debug else "S3/s3.ui.datatable.min.js")

    _log_debug(f"DataTables scripts added. Options: {options}")


# =============================================================================
# ExtJS Includes
# =============================================================================

def _extjs_xtheme_tag(appname, xtheme, path):
    """Construct <link> tag for ExtJS theme CSS."""
    if xtheme:
        return (
            f"<link href='/{appname}/static/themes/{xtheme}' "
            f"rel='stylesheet' type='text/css' />"
        )
    return None


def include_ext_js():
    """
    Include ExtJS resources for map components.

    Handles:
        - CDN vs local source selection
        - Debug vs minified versions
        - XTheme injection
        - Avoids duplicate inclusion via s3.ext_included
    """

    s3 = current.response.s3
    if s3.ext_included:
        _log_debug("ExtJS already included — skipping.")
        return

    request = current.request
    app = request.application

    xtheme = current.deployment_settings.get_base_xtheme()
    if xtheme:
        xtheme = f"{xtheme[:-3]}min.css"

    base = "//cdn.sencha.com/ext/gpl/3.4.1.1" if s3.cdn else f"/{app}/static/scripts/ext"

    if s3.debug:
        adapter = f"{base}/adapter/jquery/ext-jquery-adapter-debug.js"
        main_js = f"{base}/ext-all-debug.js"
        main_css = f"<link href='{base}/resources/css/ext-all-notheme.css' rel='stylesheet' type='text/css' />"
        theme_css = f"<link href='{base}/resources/css/xtheme-gray.css' rel='stylesheet' type='text/css' />" if not xtheme else None
    else:
        adapter = f"{base}/adapter/jquery/ext-jquery-adapter.js"
        main_js = f"{base}/ext-all.js"
        main_css = f"<link href='/{app}/static/scripts/ext/...-notheme.min.css' rel='stylesheet' type='text/css' />"
        theme_css = None

    scripts = s3.scripts
    scripts.append(adapter)
    scripts.append(main_js)

    _log_debug(f"ExtJS scripts added: adapter={adapter}, main_js={main_js}")

    langfile = f"ext-lang-{s3.language}.js"
    lang_path = os.path.join(request.folder, "static", "scripts", "ext", "src", "locale", langfile)

    if os.path.exists(lang_path):
        scripts.append(f"{base}/src/locale/{langfile}")
        _log_debug(f"ExtJS locale added: {langfile}")

    inject = s3.jquery_ready.append
    css_tag = theme_css or main_css
    inject(f"$('#ext-styles').after(\"{css_tag}\").remove()")

    s3.ext_included = True


# =============================================================================
# Underscore.js Includes
# =============================================================================

def include_underscore_js():
    """
    Include Underscore.js, using CDN when configured.

    Used by:
        - Map templates
        - GroupedOptsWidget
    """

    s3 = current.response.s3
    debug = s3.debug
    scripts = s3.scripts

    if s3.cdn:
        base = "//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.6.0/"
        script = base + ("underscore.js" if debug else "underscore-min.js")
    else:
        script = URL(c="static", f=f"scripts/underscore{'-min' if not debug else ''}.js")

    if script not in scripts:
        scripts.append(script)
        _log_debug(f"Underscore.js added: {script}")


# =============================================================================
# Developer Training Notes (Training Maintenance)
# =============================================================================
#
# HOW TO ADD A NEW JS FILE:
#   1. Place it under static/scripts/
#   2. Add it to sahana.js.cfg OR call _append_script()
#
# HOW TO ADD A NEW CSS FILE:
#   1. Place it under static/styles/
#   2. Add the filename to modules/templates/<theme>/css.cfg
#
# Debugging Tips:
#   - Set s3.debug = True for readable (non-minified) files
#   - Use current.log to trace loading behaviour
#   - If ExtJS fails to load, check CDN settings and theme paths
#
# These notes reduce onboarding time for new developers and prevent
# common mistakes during maintenance or UI extension.
#
# =============================================================================

# END OF FILE
