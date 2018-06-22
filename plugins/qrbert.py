from rtmbot.core import Plugin
from PIL import Image
import io
import json
import requests
import zbarlight
from urllib.parse import urlparse, parse_qs

# TODO
# Come up with some TODOs

class QRBert(Plugin):

    #def catch_all(self, data):
    #    print(json.dumps(data, indent=4))

    def process_message(self, data):
        if data.get('subtype', '') == 'file_share':
            if data.get('file', {}).get('mimetype', '').startswith('image'):
                self.slack_client.api_call(
                  'reactions.add',
                  name = 'eyes',
                  file = data.get('file',{}).get('id'),
                )
                user = self.slack_client.api_call(
                    'users.info',
                    user = data['user']
                ).get('user', {}).get('real_name')
                resp = self.do_image(
                    data.get('file', {}).get('url_private',''),
                    user=user
                )
                self.slack_client.api_call(
                  'reactions.remove',
                  name = 'eyes',
                  file = data.get('file',{}).get('id'),
                )
                # print (json.dumps(data.get('file'), indent=4))
                if resp:
                    # add as a file comment (doesn't work?)
                    #self.slack_client.api_call(
                    #  'files.comments.add',
                    #  comment = 'FOO: ' + resp,
                    #  file = data.get('file',{}).get('id'),
                    #))

                    # Send as message to the channel
                    self.outputs.append([
                        data['channel'], 
                        resp
                    ])

                    # Post a reply to the file's thread (mobile users can't 
                    # see these?)
                    self.slack_client.api_call(
                        'chat.postMessage',
                        channel=data['channel'],
                        text=resp,
                        as_user=True,
                        thread_ts=data['ts']
                    )
                    self.slack_client.api_call(
                      'reactions.add',
                      name = 'musical_keyboard',
                      file = data.get('file',{}).get('id'),
                    )
      
    def fetch_image(self, url):
        r = requests.get(url, headers={
            'Authorization' : 'Bearer %s' % self.slack_client.token,
        })
        r.raise_for_status()
        i = Image.open(io.BytesIO(r.content))
        i.load()
        return i

      
    def scan_image(self, img):
        ret = []
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
                    if c not in ret:
                        ret.append(c)
        return ret

    def process_serial(self, s):
        """Massage found serial numbers to the format management
           systems expect"""
        if s.startswith('LBADTN'):
            return 'ADTN' + s[6:].lower()
        if s.startswith('CXNK'):
            return s[-6:].lower()
        #else
        return s

    def is_serial(self, s):
        prefixes = ['LBAD', 'S162V', 'S172V', '261', 'CXNK']
        for p in prefixes:
          if s.startswith(p):
            return True
        return False

    def do_image(self, url, user=None):
        ret = None
        try:
            i = self.fetch_image(url)
            codes = self.scan_image(i)
            if codes:
                serials = []
                if user:
                    ret = "Found some scannable codes in {}'s image:\n".format(user)
                else:
                    ret = 'Found some scannable codes in that image:\n'
                for c in sorted(codes):
                    if self.is_serial(c):
                      serials.append(c)
                    ret += "\t*%s*\n" % c
                    q = parse_qs(urlparse(c).query)
                    if q:
                        for k in sorted(q.keys()):
                          ret += "\t\t%s -> *%s*\n" % (k, ','.join(q[k]))
                          if k == 'sn':
                            serials.extend(q[k])
                if serials: ret += "\n"
                for s in serials:
                  ret += "\t\tMaybe a serial number: *%s*\n" % self.process_serial(s)
        except Exception as e:
          print ("Oops: %r" % e)
        return ret
      
          
        
    
