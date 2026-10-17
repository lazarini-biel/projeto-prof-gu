"""
Atalho: o motor de ícones agora mora em ferramentas/iconewin.py (compartilhado
com o Mixer). Este arquivo só reexporta para manter `import icones` funcionando.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ferramentas.iconewin import para_web, disponivel   # noqa: E402,F401
