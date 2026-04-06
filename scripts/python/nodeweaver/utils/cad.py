"""
CAD Utilities for Houdini
Provides unit conversion and other CAD-like functionality for parameters.
Place this file in your Houdini python path (e.g., $HOUDINI_USER_PREF_DIR/scripts/python/)
"""

import hou

# Unit conversions TO METERS
# Format: (label, multiplier_to_meters)
UNIT_CONVERSIONS = [
    ("Feet", 0.3048),
    ("Inches", 0.0254),
    ("Centimeters", 0.01),
    ("Millimeters", 0.001),
    ("Yards", 0.9144),
    ("Kilometers", 1000.0),
    ("Miles", 1609.344),
    ("Meters", 1.0),
]


def _get_or_create_conv_unit_parm(node):
    """
    Gets the conv_unit parameter if it exists, otherwise creates it.
    Creates a menu for unit selection and a hidden float for the multiplier.
    Returns the float parameter used in expressions.
    """
    existing_parm = node.parm("conv_unit")
    if existing_parm is not None:
        return existing_parm

    # Build menu tokens and labels
    menu_items = []
    menu_labels = []
    for label, value in UNIT_CONVERSIONS:
        menu_items.append(str(value))
        menu_labels.append(label)

    # Hidden float that holds the actual multiplier (referenced in expressions)
    conv_float = hou.FloatParmTemplate(
        name="conv_unit",
        label="Conversion Multiplier",
        num_components=1,
        default_value=(UNIT_CONVERSIONS[0][1],),
        is_hidden=True,
        help="Holds the conversion multiplier (set by the unit menu)",
    )

    # Visible menu for unit selection with a callback that updates the float
    conv_menu = hou.MenuParmTemplate(
        name="conv_unit_menu",
        label="Convert From (To Meters)",
        menu_items=menu_items,
        menu_labels=menu_labels,
        default_value=0,
        script_callback=(
            'node = kwargs["node"]\n'
            'token = node.parm("conv_unit_menu").menuItems()[node.parm("conv_unit_menu").eval()]\n'
            'node.parm("conv_unit").set(float(token))'
        ),
        script_callback_language=hou.scriptLanguage.Python,
        help="Select the unit to convert FROM (to meters)",
    )

    ptg = node.parmTemplateGroup()
    ptg.insertBefore(ptg.entries()[0], conv_menu)
    ptg.insertAfter(conv_menu, conv_float)
    node.setParmTemplateGroup(ptg)

    return node.parm("conv_unit")


def _create_converted_parm(node, source_parm_name):
    """
    Creates a locked converted parameter that references the source parameter.
    If the source is part of a multi-component tuple (e.g. tx/ty/tz),
    creates a matching multi-component converted parm for the whole tuple.
    Takes the source parm NAME (string) to avoid stale hou.Parm references
    after setParmTemplateGroup calls.
    """
    # Re-fetch source parm fresh (may have been invalidated by prior setParmTemplateGroup)
    source_parm = node.parm(source_parm_name)
    if source_parm is None:
        hou.ui.displayMessage(
            f"Could not find parameter '{source_parm_name}'.",
            severity=hou.severityType.Error,
        )
        return None

    # Resolve to the full tuple so we always convert all components
    parm_tuple = source_parm.tuple()
    tuple_name = parm_tuple.name() if parm_tuple else source_parm_name
    num_components = len(parm_tuple) if parm_tuple else 1

    converted_name = f"{tuple_name}_convert"

    # Check if it already exists
    if node.parmTuple(converted_name) is not None:
        hou.ui.displayMessage(
            f"Converted parameter '{converted_name}' already exists.",
            severity=hou.severityType.Warning,
        )
        return node.parmTuple(converted_name)

    source_template = source_parm.parmTemplate()
    source_label = source_template.label()
    converted_label = f"{source_label} (Converted)"

    converted_template = hou.FloatParmTemplate(
        name=converted_name,
        label=converted_label,
        num_components=num_components,
        default_value=(0.0,) * num_components,
        help=f"Auto-converted value of {tuple_name} (in meters)",
    )

    # Find position to insert after the source parameter's template
    ptg = node.parmTemplateGroup()
    source_pt = ptg.find(tuple_name)

    if source_pt is not None:
        ptg.insertAfter(source_pt, converted_template)
    else:
        # Fallback: insert before the conv_unit controls
        conv_pt = ptg.find("conv_unit_menu")
        if conv_pt:
            ptg.insertBefore(conv_pt, converted_template)
        else:
            ptg.append(converted_template)

    node.setParmTemplateGroup(ptg)

    # Re-fetch by name after template group rebuild, then set expressions and lock
    converted_tuple = node.parmTuple(converted_name)
    source_tuple = node.parmTuple(tuple_name)
    if converted_tuple and source_tuple:
        for src_p, conv_p in zip(source_tuple, converted_tuple):
            expression = f'ch("{src_p.name()}") * ch("conv_unit")'
            conv_p.setExpression(expression, hou.exprLanguage.Hscript)
            conv_p.lock(True)

    return converted_tuple


def add_unit_conversion(kwargs):
    """
    Main entry point called from PARMmenu.xml.
    Adds unit conversion functionality to the selected parameter.
    """
    parms = kwargs.get("parms", [])
    if not parms:
        hou.ui.displayMessage("No parameter selected.", severity=hou.severityType.Error)
        return

    parm = parms[0]
    node = parm.node()
    parm_name = parm.name()  # Capture name before any setParmTemplateGroup calls

    # Check if parameter is numeric
    template = parm.parmTemplate()
    if not isinstance(template, (hou.FloatParmTemplate, hou.IntParmTemplate)):
        hou.ui.displayMessage(
            "Unit conversion only works on numeric parameters.", severity=hou.severityType.Error
        )
        return

    # Ensure conv_unit exists (may call setParmTemplateGroup, invalidating parm refs)
    _get_or_create_conv_unit_parm(node)

    # Create the converted parameter using name string, not stale parm object
    _create_converted_parm(node, parm_name)

    hou.ui.displayMessage(
        f"Added conversion for '{parm.name()}'.\n"
        f"Set 'Conversion Unit' to your input unit, enter values in that unit, "
        f"and the '_convert' parameter will show the value in meters."
    )


def is_numeric_parm(parm):
    """
    Check if the parameter is numeric (float or int).
    Used for context expression in menu.
    """
    if parm is None:
        return False
    template = parm.parmTemplate()
    return isinstance(template, (hou.FloatParmTemplate, hou.IntParmTemplate))
