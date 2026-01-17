"""
Script để insert fake data với tất cả layout types cho trang home
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, db
from sqlalchemy import func
from datetime import datetime, timedelta

def create_fake_articles():
    """Tạo fake articles với tất cả layout types"""
    
    base_date = datetime.now()
    
    articles = [
        # ===== LAYOUT 1: 1 Article Full Width (t46) =====
        {
            'element_guid': 'fake-1-full-001',
            'title': 'Pressemøde om amerikansk delegations besøg i Danmark - Full Width Article',
            'slug': 'pressemode-om-amerikansk-delegations-besog-i-danmark',
            'published_url': '/samfund/pressemode-om-amerikansk-delegations-besog-i-danmark/2331441',
            'k5a_url': '/a/2331441',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2331441',
            'published_date': base_date - timedelta(hours=2),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 0,
            'layout_type': '1_full',
            'layout_data': None,
            'image_data': {
                'element_guid': 'img-1-full-001',
                'desktop_webp': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=2116&height=1418&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=2116&height=1418&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=960&height=644&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=960&height=644&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=960&height=644&format=jpg',
                'desktop_width': '1058',
                'desktop_height': '709',
                'mobile_width': '480',
                'mobile_height': '322',
                'alt': 'Pressemøde om amerikansk delegations besøg',
                'title': 'Pressemøde om amerikansk delegations besøg i Danmark'
            }
        },
        
        # ===== LAYOUT 2: 2 Articles 1 Row (t38) =====
        {
            'element_guid': 'fake-2-articles-001',
            'title': 'Trumps særlige udsending vil besøge Grønland i marts',
            'slug': 'trumps-saerlige-udsending-vil-besoge-gronland-i-marts',
            'published_url': '/samfund/trumps-saerlige-udsending-vil-besoge-gronland-i-marts/2331321',
            'k5a_url': '/a/2331321',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2331321',
            'published_date': base_date - timedelta(hours=4),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 1,
            'layout_type': '2_articles',
            'layout_data': None,
            'image_data': {
                'element_guid': 'img-2-articles-001',
                'desktop_webp': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=1058&height=688&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=1058&height=688&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=960&height=624&format=jpg',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Trumps særlige udsending',
                'title': 'Trumps særlige udsending vil besøge Grønland i marts'
            }
        },
        {
            'element_guid': 'fake-2-articles-002',
            'title': 'Trump sætter igen gang i forretningen',
            'slug': 'trump-saetter-igen-gang-i-forretningen',
            'published_url': '/erhverv/trump-saetter-igen-gang-i-forretningen/2328783',
            'k5a_url': '/a/2328783',
            'section': 'erhverv',
            'site_alias': 'sermitsiaq',
            'instance': '2328783',
            'published_date': base_date - timedelta(hours=5),
            'is_paywall': True,
            'paywall_class': 'paywall',
            'display_order': 2,
            'layout_type': '2_articles',
            'layout_data': None,
            'image_data': {
                'element_guid': 'img-2-articles-002',
                'desktop_webp': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=1058&height=688&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=1058&height=688&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=960&height=624&format=jpg',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Trump sætter igen gang i forretningen',
                'title': 'Trump sætter igen gang i forretningen'
            }
        },
        
        # ===== LAYOUT 3: 3 Articles 1 Row (t24) =====
        {
            'element_guid': 'fake-3-articles-001',
            'title': 'Jens-Frederik Nielsen takker Vivian Motzfeldt: Arbejdsgruppe er vigtigt skridt',
            'slug': 'jens-frederik-nielsen-takker-vivian-motzfeldt',
            'published_url': '/samfund/jens-frederik-nielsen-takker-vivian-motzfeldt/2330682',
            'k5a_url': '/a/2330682',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2330682',
            'published_date': base_date - timedelta(hours=6),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 3,
            'layout_type': '3_articles',
            'layout_data': None,
            'image_data': {
                'element_guid': 'img-3-articles-001',
                'desktop_webp': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=706&height=460&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=706&height=460&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=960&height=624&format=jpg',
                'desktop_width': '353',
                'desktop_height': '230',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Jens-Frederik Nielsen takker Vivian Motzfeldt',
                'title': 'Jens-Frederik Nielsen takker Vivian Motzfeldt'
            }
        },
        {
            'element_guid': 'fake-3-articles-002',
            'title': 'Fortrøstningsfuldt og håbefuldt at der kommer dialog – vi må se om der kan findes løsning på bekymring',
            'slug': 'fortrostningsfuldt-og-habefuldt',
            'published_url': '/samfund/fortrostningsfuldt-og-habefuldt/2330624',
            'k5a_url': '/a/2330624',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2330624',
            'published_date': base_date - timedelta(hours=7),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 4,
            'layout_type': '3_articles',
            'layout_data': {'kicker': 'PIPALUK LYNGE OM USA-MØDE'},
            'image_data': {
                'element_guid': 'img-3-articles-002',
                'desktop_webp': 'https://image.sermitsiaq.ag/2330653.webp?imageId=2330653&width=706&height=460&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2330653.webp?imageId=2330653&width=706&height=460&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2330653.webp?imageId=2330653&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2330653.webp?imageId=2330653&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2330653.webp?imageId=2330653&width=960&height=624&format=jpg',
                'desktop_width': '353',
                'desktop_height': '230',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Fortrøstningsfuldt og håbefuldt',
                'title': 'Fortrøstningsfuldt og håbefuldt'
            }
        },
        {
            'element_guid': 'fake-3-articles-003',
            'title': 'Se billederne: Kom med bag kulisserne ved historisk møde',
            'slug': 'se-billederne-kom-med-bag-kulisserne',
            'published_url': '/samfund/se-billederne-kom-med-bag-kulisserne/2330481',
            'k5a_url': '/a/2330481',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2330481',
            'published_date': base_date - timedelta(hours=8),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 5,
            'layout_type': '3_articles',
            'layout_data': {'kicker': 'MØDE I WASHINGTON'},
            'image_data': {
                'element_guid': 'img-3-articles-003',
                'desktop_webp': 'https://image.sermitsiaq.ag/2330502.webp?imageId=2330502&width=706&height=460&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2330502.webp?imageId=2330502&width=706&height=460&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2330502.webp?imageId=2330502&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2330502.webp?imageId=2330502&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2330502.webp?imageId=2330502&width=960&height=624&format=jpg',
                'desktop_width': '353',
                'desktop_height': '230',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Se billederne: Kom med bag kulisserne',
                'title': 'Se billederne: Kom med bag kulisserne'
            }
        },
        
        # ===== LAYOUT 4: 1 Article Special Background (bg-black) =====
        {
            'element_guid': 'fake-1-special-bg-001',
            'title': 'Vi gambler ikke med vores ret til selvbestemmelse',
            'slug': 'vi-gambler-ikke-med-vores-ret-til-selvbestemmelse',
            'published_url': '/samfund/vi-gambler-ikke-med-vores-ret-til-selvbestemmelse/2329657',
            'k5a_url': '/a/2329657',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2329657',
            'published_date': base_date - timedelta(hours=10),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 6,
            'layout_type': '1_special_bg',
            'layout_data': {'kicker': 'JENS-FREDERIK NIELSEN'},
            'image_data': {
                'element_guid': 'img-1-special-bg-001',
                'desktop_webp': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=2116&height=1376&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=2116&height=1376&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2329660.webp?imageId=2329660&width=960&height=624&format=jpg',
                'desktop_width': '1058',
                'desktop_height': '688',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Vi gambler ikke med vores ret til selvbestemmelse',
                'title': 'Vi gambler ikke med vores ret til selvbestemmelse'
            }
        },
        
        # ===== LAYOUT 5: 1 Article + List Left =====
        {
            'element_guid': 'fake-1-with-list-left-001',
            'title': 'J.D. Vance deltager på møde med Danmark og Grønland',
            'slug': 'jd-vance-deltager-pa-mode-med-danmark-og-gronland',
            'published_url': '/samfund/jd-vance-deltager-pa-mode-med-danmark-og-gronland/2329163',
            'k5a_url': '/a/2329163',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2329163',
            'published_date': base_date - timedelta(hours=12),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 7,
            'layout_type': '1_with_list_left',
            'layout_data': {
                'list_title': 'NUUK',
                'list_items': [
                    {'title': 'Trump sætter igen gang i forretningen', 'url': '/erhverv/trump-saetter-igen-gang-i-forretningen/2328783'},
                    {'title': 'Hercules fly landede i Nuuk onsdag', 'url': '/samfund/hercules-fly-landede-i-nuuk-onsdag/2330773'},
                    {'title': 'Torsdagens atlantflyvning er aflyst', 'url': '/samfund/torsdagens-atlantflyvning-er-aflyst/2330541'},
                    {'title': 'Demonstration i Nuuk mod USA\'s planer om annektering', 'url': '/samfund/demonstration-i-nuuk-mod-usas-planer-om-annektering/2330522'},
                    {'title': 'Se billeder: Flager for solidaritet og sammenhold', 'url': '/samfund/se-billeder-flager-for-solidaritet-og-sammenhold/2329979'},
                    {'title': 'Naalakkersuisut bekræfter: Forsvaret vil sende forstærkninger til Grønland', 'url': '/samfund/naalakkersuisut-bekraefter-forsvaret-vil-sende-forstaerkninger-til-gronland/2329812'}
                ]
            },
            'image_data': {
                'element_guid': 'img-1-with-list-left-001',
                'desktop_webp': 'https://image.sermitsiaq.ag/2329168.webp?imageId=2329168&width=1058&height=688&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2329168.webp?imageId=2329168&width=1058&height=688&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2329168.webp?imageId=2329168&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2329168.webp?imageId=2329168&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2329168.webp?imageId=2329168&width=960&height=624&format=jpg',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'J.D. Vance deltager på møde',
                'title': 'J.D. Vance deltager på møde med Danmark og Grønland'
            }
        },
        
        # ===== LAYOUT 6: 1 Article + List Right =====
        {
            'element_guid': 'fake-1-with-list-right-001',
            'title': 'Trump: Nato bør bane vej for USA\'s overtagelse af Grønland',
            'slug': 'trump-nato-bor-bane-vej-for-usas-overtagelse-gronland',
            'published_url': '/samfund/trump-nato-bor-bane-vej-for-usas-overtagelse-gronland/2329876',
            'k5a_url': '/a/2329876',
            'section': 'samfund',
            'site_alias': 'sermitsiaq',
            'instance': '2329876',
            'published_date': base_date - timedelta(hours=14),
            'is_paywall': False,
            'paywall_class': '',
            'display_order': 8,
            'layout_type': '1_with_list_right',
            'layout_data': {
                'list_title': 'SENESTE',
                'list_items': [
                    {'title': 'Pressemøde om amerikansk delegations besøg i Danmark', 'url': '/samfund/pressemode-om-amerikansk-delegations-besog-i-danmark/2331441'},
                    {'title': 'Trump sætter igen gang i forretningen', 'url': '/erhverv/trump-saetter-igen-gang-i-forretningen/2328783'},
                    {'title': 'Tekniske problemer skaber forsinkelser i Østgrønland', 'url': '/samfund/tekniske-problemer-skaber-forsinkelser-i-ostgronland/2331313'},
                    {'title': 'Trumps særlige udsending vil besøge Grønland i marts – mener der bør indgås en aftale', 'url': '/samfund/trumps-saerlige-udsending-vil-besoge-gronland-i-marts-mener-der-bor-indgas-en-aftale/2331321'},
                    {'title': 'Trump kom 139 år for sent til Grønland', 'url': '/samfund/trump-kom-139-ar-for-sent-til-gronland/2328593'},
                    {'title': 'Ung anholdt for røveri i Maniitsoq', 'url': '/samfund/ung-anholdt-for-roveri-i-maniitsoq/2331266'}
                ]
            },
            'image_data': {
                'element_guid': 'img-1-with-list-right-001',
                'desktop_webp': 'https://image.sermitsiaq.ag/2329892.webp?imageId=2329892&width=1058&height=688&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2329892.webp?imageId=2329892&width=1058&height=688&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2329892.webp?imageId=2329892&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2329892.webp?imageId=2329892&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2329892.webp?imageId=2329892&width=960&height=624&format=jpg',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': 'Trump: Nato bør bane vej',
                'title': 'Trump: Nato bør bane vej for USA\'s overtagelse af Grønland'
            }
        },
    ]
    
    return articles

def main():
    """Insert fake articles vào database"""
    with app.app_context():
        print("=" * 60)
        print("📝 Inserting Fake Home Data")
        print("=" * 60)
        print()
        
        # Xóa các fake articles cũ (nếu có)
        print("🗑️  Cleaning old fake articles...")
        deleted = Article.query.filter(Article.element_guid.like('fake-%')).delete()
        db.session.commit()
        print(f"   ✅ Deleted {deleted} old fake articles")
        print()
        
        # Tạo fake articles
        print("📝 Creating fake articles...")
        fake_articles = create_fake_articles()
        
        articles_created = 0
        for article_data in fake_articles:
            try:
                article = Article(**article_data)
                db.session.add(article)
                articles_created += 1
            except Exception as e:
                print(f"   ⚠️  Error creating article {article_data.get('element_guid')}: {e}")
        
        db.session.commit()
        print(f"   ✅ Created {articles_created} fake articles")
        print()
        
        # Thống kê theo layout_type
        print("📊 Statistics by layout_type:")
        layout_types = db.session.query(Article.layout_type, func.count(Article.id))\
                                  .filter(Article.element_guid.like('fake-%'))\
                                  .group_by(Article.layout_type).all()
        for layout_type, count in layout_types:
            print(f"   - {layout_type}: {count} articles")
        print()
        
        print("=" * 60)
        print("✅ Fake data inserted successfully!")
        print("=" * 60)
        print()
        print("🌐 Visit http://localhost:5000/home to see the home page")
        print()

if __name__ == '__main__':
    main()

