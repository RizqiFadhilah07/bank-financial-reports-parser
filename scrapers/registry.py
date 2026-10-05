from .bca_scraper import BcaScraper
from .mandiri_scraper import MandiriScraper
from .bsi_scraper import BsiScraper
from .cimb_scraper import CimbScraper
from .ocbc_scraper import OcbcScraper
from .mega_scraper import MegaScraper
from .aladin_scraper import AladinScraper
from .btpn_scraper import BtpnScraper
from .uob_scraper import UobScraper
from .bni_scraper import BniScraper
from .btn_scraper import BtnScraper
from .bsn_scraper import BsnScrapper
from .megaSyariah_scraper import MegaSyariahScraper

SCRAPER_REGISTRY = {
    "BCA": BcaScraper,
    "Mandiri": MandiriScraper,
    "BSI": BsiScraper,
    "CIMB": CimbScraper,
    "OCBC": OcbcScraper,
    "Mega": MegaScraper,
    "Aladin": AladinScraper,
    "BTPN": BtpnScraper,
    "UOB": UobScraper,
    "BNI": BniScraper,
    "BTN": BtnScraper,
    "BSN" : BsnScrapper,
    "MegaSyariah": MegaSyariahScraper,
}   