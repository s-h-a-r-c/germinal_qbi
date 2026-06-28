"""Proteinmaxx: fetch protein name and sequence from an NCBI protein page URL."""

import os
import re
import urllib.request
import urllib.parse


def _accession_from_url(url: str) -> str:
    """Extract accession ID from an NCBI protein URL."""
    # Strip trailing slash and take the last path segment
    path = urllib.parse.urlparse(url).path.rstrip("/")
    accession = path.split("/")[-1]
    if not accession:
        raise ValueError(f"Could not extract accession from URL: {url}")
    return accession


def _fetch_genbank(accession: str) -> str:
    efetch = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=protein&id={urllib.parse.quote(accession)}&rettype=gb&retmode=text"
    )
    with urllib.request.urlopen(efetch, timeout=30) as response:
        return response.read().decode("utf-8")


def _parse_gene_name(genbank_text: str) -> str:
    match = re.search(r'/gene="([^"]+)"', genbank_text)
    if not match:
        raise ValueError("Could not find /gene= entry in GenBank record")
    return match.group(1)


def _parse_sequence(genbank_text: str) -> str:
    origin_match = re.search(r"^ORIGIN\s*\n(.*?)(?:^//)", genbank_text, re.MULTILINE | re.DOTALL)
    if not origin_match:
        raise ValueError("Could not find ORIGIN section in GenBank record")
    origin_block = origin_match.group(1)
    # Strip line numbers and whitespace, keep only letters
    sequence = re.sub(r"[^a-zA-Z]", "", origin_block)
    return sequence.upper()


def _unique_path(path: str) -> str:
    """Return path if it doesn't exist, otherwise append _1, _2, etc. until unique."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        candidate = f"{base}_{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def fetch_protein_info(url: str) -> tuple[str, str]:
    """Return (gene_name, sequence) for the protein at the given NCBI URL."""
    accession = _accession_from_url(url)
    genbank_text = _fetch_genbank(accession)
    gene_name = _parse_gene_name(genbank_text)
    sequence = _parse_sequence(genbank_text)
    return gene_name, sequence


def create_target_config(pdb_path: str, hotspots: list[str], configs_target_dir: str) -> str:
    """Write a Hydra target config YAML derived from pdb_path and return the file path."""
    pdb_stem = os.path.splitext(os.path.basename(pdb_path))[0]  # e.g. "SYT4" or "SYT4_1"
    config_name = pdb_stem.lower()                               # e.g. "syt4" or "syt4_1"
    config_path = _unique_path(os.path.join(configs_target_dir, f"{config_name}.yaml"))
    contents = (
        f"# @package target\n"
        f"# {pdb_stem} target configuration\n"
        f"\n"
        f'target_name: "{config_name}"\n'
        f'target_pdb_path: "pdbs/{os.path.basename(pdb_path)}"\n'
        f"# Ensure chains in PDB have the right chain IDs (ideally A, B, C, etc.)\n"
        f'target_chain: "A"\n'
        f"# binder chain should always be the last chain (e.g. \"B\" for 1 chain target, \"C\" for 2 chain target, \"D\" for 3 chain target, etc.)\n"
        f'binder_chain: "B"\n'
        f'target_hotspots: "{",".join(hotspots)}"\n'
    )
    with open(config_path, "w") as f:
        f.write(contents)
    print(f"Target config saved to {config_path}")
    return config_path


def identify_hotspots(pdb_path: str, top_n: int = 3) -> list[str]:
    """Return the top_n residues by total SASA, formatted as '{chain}{res_num}'."""
    import freesasa

    structure = freesasa.Structure(pdb_path)
    result = freesasa.calc(structure)

    residues = []
    for chain, chain_residues in result.residueAreas().items():
        for res_num, area in chain_residues.items():
            residues.append((chain, res_num, area.total))

    residues.sort(key=lambda r: r[2], reverse=True)
    return [f"{chain}{res_num}" for chain, res_num, _ in residues[:top_n]]


def fold_and_save(gene_name: str, sequence: str, pdbs_dir: str) -> str:
    """Fold a protein sequence via the ESMAtlas API and save the result as a PDB file."""
    print(f"Folding {gene_name} sequence with ESMFold...")
    req = urllib.request.Request(
        "https://api.esmatlas.com/foldSequence/v1/pdb/",
        data=sequence.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        pdb_text = response.read().decode("utf-8")

    pdb_path = _unique_path(os.path.join(pdbs_dir, f"{gene_name}.pdb"))
    with open(pdb_path, "w") as f:
        f.write(pdb_text)
    print(f"PDB file saved to {pdb_path}")
    return pdb_path
