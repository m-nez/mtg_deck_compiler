#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
    MTG deck compiler
    Copyright (C) 2016, 2017 Michał Nieznański

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
import requests
import os.path
import urllib
import argparse
import uuid
import logging
from subprocess import call
from fpdf import FPDF

def exists_abort(*args):
    for p in args:
        if os.path.exists(p):
            ans = input("".join(["Warning: ",
                p, " already exists. Do you want to overwrite it? [y/n] "]))
            if ans != "y":
                print("Aborting")
                exit(0)
        
class MagicCards:
    _root = "http://magiccards.info"

    def make_query(cardname):
        cname = cardname.replace(" ", "+")
        query = "http://magiccards.info/query?q=%s&v=card&s=cname" % cname
        return query

    def img_url(site, card):
        m = re.search(r'img\s+src="([^"]+)"\s+alt="%s"' % card, site, re.M)
        if m == None:
            raise LookupError("Could not find image for: %s" % card)
        return m.group(1)

    def change_lang(url, lang):
        spl = url.split("/")
        spl[2] = language
        return "/".join(spl)

    @classmethod
    def get_img_url(cls, card):
        q = MagicCards.make_query(card)
        r = requests.get(q)
        url = MagicCards.img_url(r.text, card)
        if not url.startswith("http://"):
            url = urllib.parse.urljoin(cls._root, url)
        return url

class Gatherer:
    def make_query(cardname):
        query = "http://gatherer.wizards.com/Pages/Search/Default.aspx?name=+[%s]" % cardname
        return query

    def get_img_url(card):
        q = Gatherer.make_query(card)
        r = requests.get(q)
        mvid = r.url[r.url.find("=") + 1:]
        url = "".join(["http://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=", mvid, "&type=card"])
        return url

class Scryfall:
    def save_img(cardname, filename):
        response = requests.get(
                "https://api.scryfall.com/cards/named",
                params={"exact" : cardname, "format" : "image"}
                )
        with open(filename, "wb") as f:
            f.write(response.content)


def save_img(url, filename):
    r = requests.get(url)
    if len(r.content) == 0:
        print("Error: Incorrect url", url, "for", filename)
        return
    with open(filename, "wb") as f:
        f.write(r.content)

class ImageMagic:
    _resolution = (312, 445)

    @classmethod
    def resize(cls, img):
        """
        Use ImageMagic to resize images to the common size
        """
        new_size = '%dx%d!' % cls._resolution
        call(['convert', img, '-resize', new_size, img])

    @classmethod
    def montage3x3(cls, images, output):
        """
        Make an image with a 3x3 table from input images
        """
        size = "%dx%d+8+8" % (cls._resolution)
        call(["montage", "-tile", "3x3", "-geometry", size, "-depth", "8", *images, output])

    @staticmethod
    def convert(images, output):
        call(["convert", *images, output])

class ImageTools:
    _w = 210
    _h = 297

    @classmethod
    def pdf_from_images(cls, images, output):
        pdf = FPDF()
        for image in images:
            pdf.add_page()
            pdf.image(image, x=0, y=0, w=cls._w, h=cls._h)
        pdf.output(output, "F")



class Compiler:
    def __init__(self, deck, directory="", prefix="page", img_format="png", overwrite=False):
        self._directory = directory
        self._deck = deck
        self._dict = {}
        self._prefix = prefix
        self._suffix = "".join([".", img_format])
        self.load_dec(deck)
        self._images = []
        self._overwrite = overwrite
    def load_dec(self, filename):
        f = open(filename, "r")
        self._dict = {}
        self._size = 0
        for l in f:
            if l[0] == "#" or l[0] == "\n":
                continue
            if l.startswith("SB:"):
                count, name = l.split(maxsplit = 2)[1:]
            else:
                count, name = l.split(maxsplit=1)   
            count = int(count)
            name = name.strip()
            if name not in self._dict:
                self._dict[name] = count
            else:
                self._dict[name] += count
            self._size += count

    def download_img(self):
        """
        Download deck cards from magiccards or gatherer
        """
        for card in self._dict:
            if self.check_cache(card):
                print("Found cached: %s" % card)
            else:
                print("Downloading: %s" % card)
                path = os.path.join(self._directory, card)
                
                exists_abort(path)
                try:
                    Scryfall.save_img(card, path)
                except Exception as e:
                    logging.info(e)
                    try:
                        url = MagicCards.get_img_url(card)
                    except LookupError as e:
                        logging.info(e)
                        url = Gatherer.get_img_url(card)
                    if not self._overwrite:
                        exists_abort(path)
                    save_img(url, path)
                ImageMagic.resize(path)
                    
    def check_cache(self, img):
        """
        Check if image is in the cache
        """
        return os.path.isfile(os.path.join(self._directory, img))

    def make_montage(self):
        num_pages = (self._size - 1) // 9 + 1
        images = [os.path.join(self._directory, im) for im in self._dict for i in range(self._dict[im])]
        self._images = []
        for i in range(num_pages):
            output = "".join([self._prefix, str(i), self._suffix])
            if not self._overwrite:
                exists_abort(output)
            ImageMagic.montage3x3(images[i * 9 : (i + 1) * 9], output)
            self._images.append(output)

    def merge_pdf(self, output):
        if not output.lower().endswith(".pdf"):
            output = "".join([output, ".pdf"])
        if not self._overwrite:
            exists_abort(output)
        ImageTools.pdf_from_images(self._images, output)

    def remove_images(self):
        call(["rm", *self._images])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="Generate pages containg up to 9 cards from a deck file.")
    parser.add_argument("deck_file",
            type=str, help="path to a deck file with each line being: quantity cardname")
    parser.add_argument("-p", "--prefix", default=uuid.uuid1().hex,
            type=str, help="prefix attached to each generated file")
    parser.add_argument("-c", "--cache", default="/tmp/mtg_deck_compiler_cache",
            type=str, help="directory with cached card images")
    parser.add_argument("-f", "--format", default="png",
            type=str, help="image format of the generated images")
    parser.add_argument("-m", "--merge", default="",
            help="path to merged pdf file generated from images")
    parser.add_argument("-k", "--keep", action="store_true",
            help="don't delete the images after generating the merged pdf")
    parser.add_argument("-o", "--overwrite", action="store_true",
            help="overwrite files without asking")
    parser.add_argument("-l", "--log-level", default="INFO", choices=["CRITICAL", "INFO"],
            help="set log level")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    if not os.path.exists(args.cache):
        os.makedirs(args.cache)

    p = Compiler(
            args.deck_file,
            directory=args.cache,
            prefix=args.prefix,
            img_format=args.format,
            overwrite=args.overwrite)
    p.download_img()
    p.make_montage()
    if args.merge:
        p.merge_pdf(args.merge)
        if not args.keep:
            p.remove_images()
