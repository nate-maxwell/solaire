"""
Application-level UI components for Solaire.

The modules in this package provide feature-specific widgets and dialogs such
as the file explorer, preference window, commit tools, structure explorer, and
about dialog. They are intentionally kept outside ``solaire.core`` because
they represent optional or replaceable application features rather than the
shared infrastructure of the editor.

The ``core`` package is reserved for foundational services and reusable editor
building blocks: event brokering, themes, tab management, the code editor,
timers, terminal integration, and other systems that multiple parts of the
application depend on. By contrast, components are higher-level interface
pieces that consume those core services.

Keeping components separate from core helps maintain a clear dependency
direction:

    components -> core

Core code should not need to know about these feature widgets directly. This
keeps the central editor infrastructure smaller, easier to test, and less
coupled to individual pieces of the user interface.
"""
