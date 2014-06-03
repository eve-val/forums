# encoding: utf-8

from __future__ import unicode_literals

import requests

from mongoengine import Document, StringField, DecimalField


OSMIUM_BASE = "http://o.smium.org"
log = __import__('logging').getLogger(__name__)

class Fit(Document):
    meta = dict(
            collection = 'Fits',
            allow_inheritance = False,
            indexes = [
                ],
        )
    
    eft = StringField(db_field='f', primary_key=True, unique=True)
    clf = StringField(db_field='c')

    dps = DecimalField(db_field='d')
    rep = DecimalField(db_field='r')
    ehp = DecimalField(db_field='e')
    isk = DecimalField(db_field='i')
    
    @staticmethod
    def get_fit(eft):
        # We do this little dance to guarantee we make only one request to osmium for an given fit.
        query = Fit.objects(eft=eft)
        if query:
            return query[0]

        f = Fit(eft=eft)
        try:
            f.save()
        except OperationError: # collision on unique field
            return Fit.objects(eft=eft).first()

        # Okay, we were the first to insert the fit into the DB. Go ahead and populate the CLF.
        
        try:
            f.fetch_osmium()
        except Exception:
            log.info("osmium failure", exc_info=True)
        
        return f.save()
    
    def fetch_osmium(self):
        resp = requests.post(OSMIUM_BASE+"/api/convert/eft/dna", data=dict(input=self.eft),
                             headers={"user-agent": "brave.forums/unversioned"})
        if resp.status_code == 200:
            self.clf = resp.text
        
            attrs = ["damage", "outgoing", "ehpAndResonances", "priceEstimateTotal"]
            attributes = "loc:ship,"+",".join(["a:"+attr for attr in attrs])
            resp = requests.get(OSMIUM_BASE+"/api/json/loadout/dna/attributes/"+attributes,
                    params={'input': self.clf},
                    headers={"user-agent": "brave.forums/unversioned"},
                    )
            if resp.status_code == 200:
                json = resp.json()
                self.dps = json['ship']['damage']['total']['dps']
                self.rep = max(json['ship']['outgoing'][tank][0] for tank in ("shield", "armor"))
                self.ehp = json['ship']['ehpAndResonances']['ehp']['avg']
                self.isk = json['ship']['priceEstimateTotal']['ship'] + json['ship']['priceEstimateTotal']['fitting']
    
    def fit_url(self):
        if not self.clf:
            return None
        return OSMIUM_BASE+"/loadout/dna/"+self.clf
    
    def stats_string(self):
        if not (self.dps or self.rep or self.ehp or self.isk):
            return None
        stats = []
        if self.rep:
            stats.append("%s reps" % format_number(self.rep))
        else:
            stats.append("%s dps" % format_number(self.dps))
        stats.append("%s ehp" % format_number(self.ehp))
        stats.append("%s isk" % format_number(self.isk))
        return " - ".join(stats)

def format_number(number):
    sizes = ['', 'k', 'M', 'G', 'T']
    index = 0
    number = float(number)
    while number > 1000.0:
        number /= 1000.0
        index += 1
    return "%3d%s" % (number, sizes[index])
