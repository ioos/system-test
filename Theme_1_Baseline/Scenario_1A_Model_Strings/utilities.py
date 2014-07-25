from IPython.core.display import HTML
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
