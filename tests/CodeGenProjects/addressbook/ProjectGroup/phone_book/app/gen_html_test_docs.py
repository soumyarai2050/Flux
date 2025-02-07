# standard imports
import os

# project imports
from FluxPythonUtils.scripts.gen_test_html_doc import gen_test_html_doc


if __name__ == "__main__":
    module_name = "test_street_book"  # Replace with your test script's module name
    html_content = gen_test_html_doc(module_name)

    docs_dir_name = "test_docs"
    if not os.path.exists(docs_dir_name):
        os.mkdir(docs_dir_name)

    gen_test_file = f"{module_name}_doc.html"
    with open(f"{docs_dir_name}/{gen_test_file}", "w") as f:
        f.write(html_content)
    print(f"HTML file generated: {gen_test_file}")