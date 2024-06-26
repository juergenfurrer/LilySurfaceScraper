# Copyright (c) 2019 - 2020 Elie Michel
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# The Software is provided “as is”, without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose and noninfringement. In no event shall
# the authors or copyright holders be liable for any claim, damages or other
# liability, whether in an action of contract, tort or otherwise, arising from,
# out of or in connection with the software or the use or other dealings in the
# Software.
#
# This file is part of LilySurfaceScraper, a Blender add-on to import materials
# from a single URL

from .AbstractScraper import AbstractScraper
import re
import os
from collections import defaultdict


class PolyHavenHdriScraper(AbstractScraper):
    scraped_type = {'WORLD'}
    source_name = "Poly Haven HDRI"
    home_url = "https://polyhaven.com/hdris"
    home_dir = "hdrihaven"

    polyHavenUrl = re.compile(r"(?:https:\/\/)?polyhaven\.com\/a\/([^\/]+)")

    @classmethod
    def getUid(cls, url):
        match = cls.polyHavenUrl.match(url)
        if match is not None:
            return match.group(1)
        return None

    @classmethod
    def canHandleUrl(cls, url):
        """Return true if the URL can be scraped by this scraper."""
        return url.startswith("https://polyhaven.com/a/")

    def getVariantList(self, url):
        """Get a list of available variants.
        The list may be empty, and must be None in case of error."""
        identifier = self.getUid(url)

        if identifier is None:
            self.error = "Bad Url"
            return None

        data = self.fetchJson(f"https://api.polyhaven.com/info/{identifier}")
        if data is None:
            self.error = "API error"
            return None
        elif data["type"] != 0:  # 0 for hdris
            self.error = "Not a texture"
            return None

        name = data["name"]

        api_url = f"https://api.polyhaven.com/files/{identifier}"
        data = self.fetchJson(api_url)
        if data is None:
            self.error = "API error"
            return None

        variant_data = defaultdict(dict)
        for res, maps in data["hdri"].items():
            for fmt, dat in maps.items():
                variant_data[(res, fmt)] = dat['url']

        variant_data = [(*k, v) for k, v in variant_data.items()]
        variant_data.sort(key=lambda x: self.sortTextWithNumbers(f"{x[1]} {x[0]}"))
        variants = [f"{res} ({fmt})" for res, fmt, _ in variant_data]

        self.metadata.name = name
        self.metadata.id = identifier
        self.metadata.setCustom("variant_data", variant_data)
        return variants

    def getThumbnail(self):
        return f"https://cdn.polyhaven.com/asset_img/thumbs/{self.metadata.id}.png?width=512&height=512"

    def fetchVariant(self, variant_index, material_data):
        """Fill material_data with data from the selected variant.
        Must fill material_data.name and material_data.maps.
        Return a boolean status, and fill self.error to add error messages."""
        # Get data saved in fetchVariantList
        name = self.metadata.name
        variant_data = self.metadata.getCustom("variant_data")
        variants = self.metadata.variants
        
        if variant_index < 0 or variant_index >= len(variants):
            self.error = "Invalid variant index: {}".format(variant_index)
            return False
        
        var_name = variants[variant_index]
        var_data = variant_data[variant_index]
        material_data.name = f"{self.home_dir}/{name}/{var_name}"

        map_url = var_data[2]
        material_data.maps['sky'] = self.fetchImage(map_url, f"{self.home_dir}/{name}", var_data[0])
        
        return True

    def isDownloaded(self, target_variation):
        root = self.getTextureDirectory(os.path.join(self.home_dir, self.metadata.name))
        name, ext = target_variation.split(" (")
        return os.path.isfile(os.path.join(root, f"{name}.{ext[:-1]}"))

    def getUrlFromName(self, asset_name):
        # data = self.fetchJson(f"https://api.polyhaven.com/assets?s={asset_name.replace()}")

        # this works well enough for most
        name = asset_name.lower().replace(' ', '_').replace("'", "")
        return f"https://polyhaven.com/a/{name}"
