import os
import subprocess, shlex
from threading import Timer

BASIC_SKELETON = r"""
\documentclass[12pt]{article}
\pagestyle{empty}
\usepackage{amsmath}
\begin{document}
\begin{displaymath}
%s
\end{displaymath}
\end{document}
"""

def run(cmd, timeout_sec):
    """Run cmd in the shell with timeout"""
    proc = subprocess.Popen(cmd, shell=True)
    kill_proc = lambda p: p.kill()
    timer = Timer(timeout_sec, kill_proc, [proc])
    try:
        timer.start()
        stdout,stderr = proc.communicate()
    finally:
        timer.cancel()

def clean(dir_output, name):
    delete_file(dir_output+"{}.aux".format(name))
    delete_file(dir_output+"{}.log".format(name))
    # delete_file(dir_output+"{}.pdf".format(name))
    delete_file(dir_output+"{}.tex".format(name))

def delete_file(path_file):
    try:
        os.remove(path_file)
    except Exception:
        pass

class tex_2_pdf: 

    def __init__(self, file_name):
        self.file_name = file_name
        self.TIMEOUT = 10
        self.dir_Output = 'sake/'
        self.name = "temp"

        self.load_latex()
        self.create_texFile()
        self.run_pdflatex()
        
    def load_latex(self):
        self.latex_code = open("{}.txt".format(self.file_name)).read()

    def create_texFile(self):
        with open(self.dir_Output+"{}.tex".format(self.name), "w") as f:
            f.write(BASIC_SKELETON % (self.latex_code))

    def run_pdflatex(self):
        run("pdflatex -interaction=nonstopmode -output-directory={} {}".format(self.dir_Output, self.dir_Output+"{}.tex".format(self.name)), self.TIMEOUT)
        clean(self.dir_Output, self.name)

    def get_pdf_name(self):
        return self.name+".pdf"


