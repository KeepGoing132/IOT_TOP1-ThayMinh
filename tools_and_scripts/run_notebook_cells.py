import json
import sys
import io
import contextlib
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run_notebook(nb_path):
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Global execution namespace
    ns = {}

    execution_count = 1

    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue

        code_text = "".join(cell['source'])
        print(f"Executing code cell {execution_count}...")

        cell['execution_count'] = execution_count
        cell['outputs'] = []

        stdout_buf = io.StringIO()

        # Custom display function
        def custom_display(obj):
            if hasattr(obj, 'to_html'):
                html_str = obj.to_html()
                cell['outputs'].append({
                    "data": {
                        "text/html": [html_str],
                        "text/plain": [str(obj)]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                })
            else:
                cell['outputs'].append({
                    "data": {
                        "text/plain": [str(obj)]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                })

        ns['display'] = custom_display

        # Track figures
        plt.close('all')

        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stdout_buf):
                exec(code_text, ns)

            out_text = stdout_buf.getvalue()
            if out_text:
                cell['outputs'].append({
                    "name": "stdout",
                    "output_type": "stream",
                    "text": [line + "\n" for line in out_text.splitlines()]
                })

            # Check if matplotlib created any figures
            figs = [plt.figure(i) for i in plt.get_fignums()]
            for fig in figs:
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', bbox_inches='tight')
                img_buf.seek(0)
                img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
                cell['outputs'].append({
                    "data": {
                        "image/png": img_base64,
                        "text/plain": ["<Figure size ...>"]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                })
            plt.close('all')

        except Exception as e:
            err_msg = f"Error in cell {execution_count}: {type(e).__name__}: {e}"
            print(err_msg)
            import traceback
            traceback.print_exc()
            cell['outputs'].append({
                "ename": type(e).__name__,
                "evalue": str(e),
                "output_type": "error",
                "traceback": traceback.format_exc().splitlines()
            })
            break

        execution_count += 1

    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"Successfully executed and updated {nb_path}!")

if __name__ == '__main__':
    run_notebook('fire_det.ipynb')
