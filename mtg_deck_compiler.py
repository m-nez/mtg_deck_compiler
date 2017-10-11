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
import shlex
import urllib
import argparse
from sys import argv

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
        command = "convert '%s' -resize %dx%d! '%s'" % (img, *cls._resolution, img)
        os.system(command)

    @classmethod
    def montage3x3(cls, images, output):
        """
        Make an image with a 3x3 table from input images
        """
        sources = " ".join(images)
        os.system("montage -tile 3x3 -geometry %dx%d+8+8 %s %s" % (*cls._resolution, sources, output))

class Compiler:
    def __init__(self, deck, directory="", prefix="page", img_format="png"):
        self._directory = directory
        self._deck = deck
        self._dict = {}
        self._prefix = prefix
        self._suffix = "".join([".", img_format])
        self.load_dec(deck)

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
                try:
                    url = MagicCards.get_img_url(card)
                    save_img(url, path)
                except LookupError as e:
                    url = Gatherer.get_img_url(card)
                    save_img(url, path)
                ImageMagic.resize(path)
                    
    def check_cache(self, img):
        """
        Check if image is in the cache
        """
        return os.path.isfile(os.path.join(self._directory, img))

    def make_montage(self):
        num_pages = (self._size - 1) // 9 + 1
        images = [shlex.quote(os.path.join(self._directory, im)) for im in self._dict for i in range(self._dict[im])]
        for i in range(num_pages):
            ImageMagic.montage3x3(images[i * 9 : (i + 1) * 9], "".join([self._prefix, str(i), self._suffix]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="Generate pages containg up to 9 cards from a deck file.")
    parser.add_argument("deck_file",
            type=str, help="path to a deck file with each line being: quantity cardname")
    parser.add_argument("output_prefix",
            type=str, help="prefix attached to each generated file")
    parser.add_argument("-c", "--cache", default="/tmp/mtg_deck_compiler_cache",
            type=str, help="directory with cached card images")
    parser.add_argument("-f", "--format", default="png",
            type=str, help="image format of the generate images")
    args = parser.parse_args()

    if not os.path.exists(args.cache):
        os.makedirs(args.cache)

    p = Compiler(args.deck_file, directory=args.cache, prefix=args.output_prefix, img_format=args.format)
    p.download_img()
    p.make_montage()
