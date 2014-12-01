"""
Utility functions
"""
from IPython.display import HTML

def inline_map(m):
    """From http://nbviewer.ipython.org/gist/rsignell-usgs/
    bea6c0fe00a7d6e3249c."""
    m._build_map()
    srcdoc = m.HTML.replace('"', '&quot;')
    embed = HTML('<iframe srcdoc="{srcdoc}" '
                 'style="width: 100%; height: 500px; '
                 'border: none"></iframe>'.format(srcdoc=srcdoc))
    return embed


def css_styles():
    return HTML("""
        <style>
        .info {
            background-color: #fcf8e3; border-color: #faebcc; border-left: 5px solid #8a6d3b; padding: 0.5em; color: #8a6d3b;
        }
        .success {
            background-color: #d9edf7; border-color: #bce8f1; border-left: 5px solid #31708f; padding: 0.5em; color: #31708f;
        }
        .error {
            background-color: #f2dede; border-color: #ebccd1; border-left: 5px solid #a94442; padding: 0.5em; color: #a94442;
        }
        .warning {
            background-color: #fcf8e3; border-color: #faebcc; border-left: 5px solid #8a6d3b; padding: 0.5em; color: #8a6d3b;
        }
        </style>
    """)