"""
Citation verification constants and data mappings.

This module contains pure data structures used throughout the citation verification
system: court mappings, international court identifiers, and hardcoded file paths.
"""

from pathlib import Path

# Get absolute path to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Hardcoded mapping for FOIA citations to local file
HARDCODED_FOIA_FILES = {
    "Freedom of Information Act 1982": str(PROJECT_ROOT / "docs" / "legislation" / "FOIA.md"),
    "Freedom of Information Act 1982 (Cth)": str(PROJECT_ROOT / "docs" / "legislation" / "FOIA.md"),
    "FOI Act 1982": str(PROJECT_ROOT / "docs" / "legislation" / "FOIA.md"),
    "FOI Act 1982 (Cth)": str(PROJECT_ROOT / "docs" / "legislation" / "FOIA.md"),
    "Freedom of Information Act 1982 (Commonwealth)": str(PROJECT_ROOT / "docs" / "legislation" / "FOIA.md"),
}

# Australian court abbreviations and their traditional paths (for URL building compatibility)
COURT_MAPPINGS = {
    "HCA": "cth/HCA",
    "FCA": "cth/FCA",
    "FCAFC": "cth/FCAFC",
    "FCFCOA": "cth/FCFCOA",
    "FedCFamC1A": "cth/FedCFamC1A",
    "FedCFamC2A": "cth/FedCFamC2A",
    "FamCA": "cth/FamCA",
    "FamCAFC": "cth/FamCAFC",
    "NSWSC": "nsw/NSWSC",
    "NSWCA": "nsw/NSWCA",
    "NSWCCA": "nsw/NSWCCA",
    "NSWDC": "nsw/NSWDC",
    "NSWLC": "nsw/NSWLC",
    "VSC": "vic/VSC",
    "VSCA": "vic/VSCA",
    "VCC": "vic/VCC",
    "VCAT": "vic/VCAT",
    "QSC": "qld/QSC",
    "QCA": "qld/QCA",
    "QDC": "qld/QDC",
    "QCAT": "qld/QCAT",
    "SASC": "sa/SASC",
    "SASCFC": "sa/SASCFC",
    "SADC": "sa/SADC",
    "SACAT": "sa/SACAT",
    "WASC": "wa/WASC",
    "WASCA": "wa/WASCA",
    "WADC": "wa/WADC",
    "WASAT": "wa/WASAT",
    "TASSC": "tas/TASSC",
    "TASFC": "tas/TASFC",
    "ACTSC": "act/ACTSC",
    "ACAT": "act/ACAT",
    "NTSC": "nt/NTSC",
    "NTCA": "nt/NTCA",
    "FCWA": "wa/FCWA",
}

# Note: Known citations database removed per user request
# The system now relies on high-authority source acceptance when verification is unavailable

# UK/International court abbreviations - historically relevant to Australian law
# These cannot be verified via AustLII but are valid citations
UK_INTERNATIONAL_COURTS = {
    # UK Courts and Reports
    "AC": "Appeal Cases (House of Lords/Privy Council)",
    "PC": "Privy Council",
    "Ch": "Chancery Division",
    "QB": "Queen's Bench Division",
    "KB": "King's Bench Division",
    "WLR": "Weekly Law Reports",
    "All ER": "All England Reports",
    "AllER": "All England Reports",  # Alternative format
    "UKHL": "UK House of Lords",
    "UKSC": "UK Supreme Court",
    "EWCA": "England and Wales Court of Appeal",
    "EWHC": "England and Wales High Court",
    "Fam": "Family Division",
    "ER": "English Reports (historical)",
    "Cr App R": "Criminal Appeal Reports",
    "CrAppR": "Criminal Appeal Reports",  # Alternative format
    "Lloyd's Rep": "Lloyd's Law Reports",
    # New Zealand
    "NZLR": "New Zealand Law Reports",
    "NZCA": "New Zealand Court of Appeal",
    "NZSC": "New Zealand Supreme Court",
    "NZHC": "New Zealand High Court",
    # Canada
    "SCR": "Supreme Court Reports (Canada)",
    "DLR": "Dominion Law Reports",
    "OR": "Ontario Reports",
    "BCR": "British Columbia Reports",
    "AR": "Alberta Reports",
    "QR": "Quebec Reports",
    "SCC": "Supreme Court of Canada",
    "ONCA": "Ontario Court of Appeal",
    "BCCA": "British Columbia Court of Appeal",
    # Singapore
    "SLR": "Singapore Law Reports",
    "SGCA": "Singapore Court of Appeal",
    "SGHC": "Singapore High Court",
    # Hong Kong
    "HKLR": "Hong Kong Law Reports",
    "HKLRD": "Hong Kong Law Reports & Digest",
    "HKCFA": "Hong Kong Court of Final Appeal",
    "HKCA": "Hong Kong Court of Appeal",
    "HKCFI": "Hong Kong Court of First Instance",
    # Malaysia
    "MLJ": "Malayan Law Journal",
    "CLJ": "Current Law Journal (Malaysia)",
    # South Africa
    "SALR": "South African Law Reports",
    "ZASCA": "South Africa Supreme Court of Appeal",
    "ZACC": "South Africa Constitutional Court",
    # International Courts
    "ICJ": "International Court of Justice",
    "ECHR": "European Court of Human Rights",
    "ECJ": "European Court of Justice",
    "ICC": "International Criminal Court",
    "ITLOS": "International Tribunal for the Law of the Sea",
    # United States (occasionally referenced)
    "US": "United States Reports (Supreme Court)",
    "S.Ct": "Supreme Court Reporter (US)",
    "SCt": "Supreme Court Reporter (US)",  # Alternative format
    "F.2d": "Federal Reporter, Second Series",
    "F.3d": "Federal Reporter, Third Series",
    "F2d": "Federal Reporter, Second Series",  # Alternative format
    "F3d": "Federal Reporter, Third Series",  # Alternative format
    # Academic and Specialist Reports
    "ICLQ": "International & Comparative Law Quarterly",
    "LQR": "Law Quarterly Review",
    "MLR": "Modern Law Review",
    "OJLS": "Oxford Journal of Legal Studies",
    "AILR": "Australian Indigenous Law Reporter",
    "IPR": "Intellectual Property Reports",
    "IPLR": "Intellectual Property Law Reports",
}
