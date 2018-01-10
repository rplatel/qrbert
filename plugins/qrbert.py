from rtmbot.core import Plugin
from PIL import Image
import io
import json
import requests
import zbarlight
from urllib.parse import urlparse, parse_qs

# TODO
# rotate image 90, 90, 90, collect all codes, unique
# make function to collect all codes ^^ then another to parse and say them
# check in to github
# requirements.txt and etc

class QRBert(Plugin):

    #def catch_all(self, data):
    #    print(json.dumps(data, indent=4))

    def process_message(self, data):
        if data.get('subtype', '') == 'file_share':
            if data.get('file', {}).get('mimetype', '').startswith('image'):
                resp = self.do_image(data.get('file', {}).get('url_private',''))
                if resp:
                  self.outputs.append([
                      data['channel'], 
                      resp
                  ])
      
    def fetch_image(self, url):
        r = requests.get(url, headers={
            'Authorization' : 'Bearer %s' % self.slack_client.token,
        })
        r.raise_for_status()
        i = Image.open(io.BytesIO(r.content))
        i.load()
        return i

      
    def scan_image(self, img):
        ret = '' 
        syms = [
            'ean13', 'upca', 'ean8', 'upce', 'code128', 'code93', 'code39',
            'i25', 'databar', 'databar-exp', 'qrcode', 'ean5', 'ean2', 
            'composite', 'isbn13', 'isbn10', 'codabar', 'pdf417'
        ]
        for s in syms:
          try:
            codes = zbarlight.scan_codes(s, img)
          except zbarlight.UnknownSymbologieError:
            continue
          if codes:
            for c in codes:
              c = c.decode()
              ret += 'Found a %s: << %s >>\n' % (s, c)
              q = parse_qs(urlparse(c).query)
              if q:
                  for (k, v) in q.items():
                      ret += "    %s -> *%s*\n" % (k, ','.join(v))
        return ret

    def do_image(self, url):
        try:
          i = self.fetch_image(url)
          return self.scan_image(i)
        except Exception as e:
          print ("Oops: %r" % e)
        return None
      
          
        
    
