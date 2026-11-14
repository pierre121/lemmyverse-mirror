#!/usr/bin/env python3
"""Construit le miroir public Lemmyverse sans publier de données invalides."""

import argparse
import json
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

URL_ARCHIVE="https://data.lemmyverse.net/data/json-bundle.zip"
FICHIERS={"instances":"instance.full.json","communities":"community.full.json"}
REPLIS={"instances":"instance.full 13Juill25.json","communities":"community.full 6Juill25.json"}
MINIMUMS={"instances":100,"communities":1000}
CHAMPS_NOMBRES={
    "instances":("users","users_active_week","posts","comments"),
    "communities":("subscribers","users_active_week","posts","comments"),
}


def validerSnapshot(chemin:Path, typeSnapshot:str, minimum:int|None=None)->int:
    with chemin.open(encoding="utf-8") as fichier:
        données=json.load(fichier)
    seuil=MINIMUMS[typeSnapshot] if minimum is None else minimum
    if isinstance(données,list) is False or len(données)<seuil:
        raise ValueError(f"Snapshot {typeSnapshot} trop petit ou illisible : {len(données) if isinstance(données,list) else 'format invalide'} entrée(s).")
    for index, entrée in enumerate(données):
        if isinstance(entrée,dict) is False or isinstance(entrée.get("baseurl"),str) is False or entrée["baseurl"]=="" or isinstance(entrée.get("counts"),dict) is False:
            raise ValueError(f"Entrée {index} invalide dans le snapshot {typeSnapshot}.")
        if typeSnapshot=="communities" and any(isinstance(entrée.get(champ),str) is False for champ in ("name","title")):
            raise ValueError(f"Entrée {index} sans nom ou titre dans le snapshot communautés.")
        if any(isinstance(entrée["counts"].get(champ),(int,float)) is False or isinstance(entrée["counts"][champ],bool) for champ in CHAMPS_NOMBRES[typeSnapshot]):
            raise ValueError(f"Compteurs invalides à l’entrée {index} du snapshot {typeSnapshot}.")
        abonnésLocaux=entrée["counts"].get("subscribers_local")
        if typeSnapshot=="communities" and abonnésLocaux is not None and (isinstance(abonnésLocaux,(int,float)) is False or isinstance(abonnésLocaux,bool)):
            raise ValueError(f"Compteur subscribers_local invalide à l’entrée {index} du snapshot communautés.")
    return len(données)


def copierArchive(zipArchive:zipfile.ZipFile, nom:str, destination:Path):
    membres=[membre for membre in zipArchive.infolist() if Path(membre.filename).name==nom]
    if len(membres)!=1:
        raise ValueError(f"Le bundle Lemmyverse doit contenir un seul fichier {nom}.")
    with zipArchive.open(membres[0]) as source, destination.open("wb") as cible:
        shutil.copyfileobj(source,cible)


def urlPrécédent(basePages:str, typeSnapshot:str)->str:
    racine=f"{basePages.rstrip('/')}/"
    return urllib.parse.urljoin(racine,f"data/{typeSnapshot}.latest.json")


def copierSnapshotPrécédent(basePages:str, typeSnapshot:str, replis:Path, destination:Path):
    if basePages!="":
        try:
            requête=urllib.request.Request(urlPrécédent(basePages,typeSnapshot),headers={"User-Agent":"zAppLemmy STORAGE-002"})
            with urllib.request.urlopen(requête,timeout=30) as réponse, destination.open("wb") as cible:
                if réponse.status!=200:
                    raise ValueError(f"Le miroir précédent répond HTTP {réponse.status}.")
                shutil.copyfileobj(réponse,cible)
        except urllib.error.HTTPError as erreur:
            if erreur.code!=404:
                raise
    if destination.exists() is False:
        fichierRepli=replis/REPLIS[typeSnapshot]
        if fichierRepli.exists() is False:
            raise FileNotFoundError(f"Snapshot antérieur absent : {fichierRepli}")
        shutil.copyfile(fichierRepli,destination)
    validerSnapshot(destination,typeSnapshot)


def téléchargerArchive(url:str,destination:Path):
    dernièreErreur=None
    for tentative in range(3):
        try:
            requête=urllib.request.Request(url,headers={"User-Agent":"zAppLemmy STORAGE-002"})
            with urllib.request.urlopen(requête,timeout=120) as réponse, destination.open("wb") as fichier:
                if réponse.status!=200:
                    raise ValueError(f"Le bundle Lemmyverse répond HTTP {réponse.status}.")
                shutil.copyfileobj(réponse,fichier)
            return
        except urllib.error.HTTPError as erreur:
            if erreur.code not in (429,500,502,503,504):
                raise
            dernièreErreur=erreur
        except (urllib.error.URLError,TimeoutError) as erreur:
            dernièreErreur=erreur
        if tentative<2:
            time.sleep(2**tentative)
    raise RuntimeError("Le téléchargement du bundle Lemmyverse a échoué après trois tentatives.") from dernièreErreur


def construireSite(archive:Path, basePages:str, destination:Path, replis:Path):
    if destination.exists():
        raise FileExistsError(f"Le répertoire de sortie existe déjà : {destination}")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lemmyverse-",dir=destination.parent) as temporaire:
        staging=Path(temporaire)
        dossierDonnées=staging/"data"
        dossierDonnées.mkdir()
        with zipfile.ZipFile(archive) as zipArchive:
            for typeSnapshot,nomArchive in FICHIERS.items():
                fichierActuel=dossierDonnées/f"{typeSnapshot}.latest.json"
                copierArchive(zipArchive,nomArchive,fichierActuel)
                validerSnapshot(fichierActuel,typeSnapshot)
                copierSnapshotPrécédent(basePages,typeSnapshot,replis,dossierDonnées/f"{typeSnapshot}.previous.json")
        métadonnées={"source":URL_ARCHIVE,"generatedAt":datetime.now(timezone.utc).isoformat(),"snapshots":["previous","latest"]}
        (dossierDonnées/"index.json").write_text(json.dumps(métadonnées,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (staging/"index.html").write_text(
            "<!doctype html><html lang=fr><meta charset=utf-8><title>Miroir Lemmyverse zAppLemmy</title>"
            "<h1>Miroir Lemmyverse zAppLemmy</h1><p>Deux snapshots publics d’instances et de communautés, actualisés chaque semaine.</p>"
            "<p><a href=data/index.json>Métadonnées et date de mise à jour</a></p></html>\n",encoding="utf-8")
        staging.rename(destination)


def main():
    analyseur=argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--pages-base",default="",help="URL de base du site GitHub Pages déjà déployé.")
    analyseur.add_argument("--output",type=Path,required=True,help="Répertoire de sortie du site statique.")
    analyseur.add_argument("--fallback",type=Path,default=Path("public/Données lemmyverse"),help="Snapshots suivis utilisés uniquement au premier déploiement.")
    analyseur.add_argument("--archive-url",default=URL_ARCHIVE,help="URL du bundle ZIP Lemmyverse.")
    arguments=analyseur.parse_args()
    with tempfile.TemporaryDirectory(prefix="lemmyverse-zip-") as temporaire:
        archive=Path(temporaire)/"json-bundle.zip"
        téléchargerArchive(arguments.archive_url,archive)
        construireSite(archive,arguments.pages_base,arguments.output,arguments.fallback)


if __name__=="__main__":
    main()
