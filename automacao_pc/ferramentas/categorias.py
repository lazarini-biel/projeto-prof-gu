"""
Tipos de arquivo -> categoria (nome da pasta de destino).
"""

CATEGORIAS = {
    "PDFs": [".pdf"],
    "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif",
                ".tif", ".tiff", ".svg", ".ico", ".raw", ".cr2", ".nef", ".arw",
                ".dng", ".psd", ".avif"],
    "Vídeos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
               ".3gp", ".mpg", ".mpeg", ".ts"],
    "Músicas": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"],
    "Planilhas": [".xlsx", ".xls", ".xlsm", ".csv", ".ods"],
    "Documentos": [".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".epub", ".mobi"],
    "Apresentações": [".ppt", ".pptx", ".odp", ".key"],
    "Instaladores": [".exe", ".msi", ".msix", ".msixbundle", ".appx", ".appxbundle"],
    "Compactados": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"],
    "Imagens de disco": [".iso", ".img", ".vhd", ".vhdx"],
    "Torrents": [".torrent"],
    "Código": [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".java",
               ".c", ".cpp", ".cs", ".sql", ".sh", ".bat", ".ps1"],
    "Fontes": [".ttf", ".otf", ".woff", ".woff2"],
}
OUTROS = "Outros"

# Downloads que ainda estão em andamento (Chrome, Edge, Firefox, Opera...).
INCOMPLETOS = {".crdownload", ".part", ".partial", ".download", ".opdownload", ".tmp"}

# Nunca são movidos.
IGNORAR_NOMES = {"desktop.ini", "thumbs.db", ".ds_store"}


def montar_mapa(extras=None):
    """Dicionário ".ext" -> categoria. `extras` (do config) acrescenta ou sobrescreve."""
    mapa = {}
    for categoria, extensoes in {**CATEGORIAS, **(extras or {})}.items():
        for ext in extensoes:
            ext = ext.lower() if ext.startswith(".") else "." + ext.lower()
            mapa[ext] = categoria
    return mapa
