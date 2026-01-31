#!/usr/bin/env python3
"""Test script để kiểm tra UNNIA kicker_floating classes"""

from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.article_parser import parse_article_element

# HTML từ user (article có UNNIA với bg-secondary)
html = """
<article data-element-guid="a71f3c7b-f056-4176-9a66-c287fdd90717" class="column small-12 large-6 small-abs-12 large-abs-6 " data-site-alias="sermitsiaq" data-section="kultur" data-instance="2336140" itemscope="">
    
    <div class="content" style="">
        
        <a itemprop="url" class="" href="/kultur/filminstruktor-har-fulgt-jens-frederik-nielsen-i-et-ar-og-sikke-et-ar/2336140" data-k5a-url="https://www.sermitsiaq.ag/a/2336140" rel="">


        <div class="media ">
                

                <figure data-element-guid="2eec1d59-f855-4207-8cb7-fe7e346a40ed" class="">
    <div class="img fullwidthTarget">
        <picture>
            <source srcset="https://image.sermitsiaq.ag/2336156.webp?imageId=2336156&amp;x=0.00&amp;y=0.00&amp;cropw=100.00&amp;croph=100.00&amp;heightx=0.00&amp;heighty=0.00&amp;heightw=100.00&amp;heighth=100.00&amp;width=960&amp;height=624&amp;format=jpg" width="480" height="312" media="(max-width: 767px)" type="image/jpeg">    
            <img src="https://image.sermitsiaq.ag/2336156.webp?imageId=2336156&amp;x=0.00&amp;y=0.00&amp;cropw=100.00&amp;croph=100.00&amp;heightx=0.00&amp;heighty=0.00&amp;heightw=100.00&amp;heighth=100.00&amp;width=960&amp;height=624&amp;format=jpg" width="480" height="312" title="Filminstruktør har fulgt Jens-Frederik Nielsen i et år – og sikke et år" alt="" loading="lazy" style="">
        </picture>        
            </div>
    
</figure>

                
                
                
                
                
                
                
            
            <div class="floatingText">
                <div style="" class="kicker floating bg-secondary color_mobile_bg-secondary hasTextPadding mobile-hasTextPadding">
UNNIA
</div>

                <div class="labels">
                </div>
            </div>
            

        </div>


        
            <h2 itemprop="headline" class="headline font-weight-normal m-font-weight-normal align-center mobile_text_align_align-center" style="">Filminstruktør har fulgt Jens-Frederik Nielsen i et år – og sikke et år
</h2>

        




        </a>

        <time itemprop="datePublished" datetime="2026-01-30T13:19:32+01:00"></time>
    </div>
</article>
"""

soup = BeautifulSoup(html, 'html.parser')
article_elem = soup.find('article')

result = parse_article_element(article_elem, 'https://www.sermitsiaq.ag')

print("=" * 80)
print("Article Data:")
print("=" * 80)
print(f"Title: {result['title']}")
print(f"URL: {result['url']}")
print(f"Section: {result['section']}")
print(f"Instance: {result['instance']}")
print()
print("=" * 80)
print("Kicker Floating:")
print("=" * 80)
print(f"kicker_floating: {result.get('kicker_floating')}")
print(f"kicker_floating_classes: {result.get('kicker_floating_classes')}")
print()

# Check nếu có bg-secondary
if result.get('kicker_floating_classes') and 'bg-secondary' in result['kicker_floating_classes']:
    print("✅ SUCCESS: bg-secondary được crawl đúng!")
else:
    print("❌ FAILED: bg-secondary KHÔNG được crawl!")

print()
print("=" * 80)
print("Content Classes:")
print("=" * 80)
print(f"content_classes: {result.get('content_classes')}")

