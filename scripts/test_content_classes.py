#!/usr/bin/env python3
"""Test script để kiểm tra content_classes được crawl đúng không"""

from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.article_parser import parse_article_element

# HTML từ user (article có bg-quaternary)
html = """
<article data-element-guid="42f52b2b-b544-4fc8-a11e-5c7c4f4e62d4" class="column paywall small-12 large-6 small-abs-12 large-abs-6 " data-site-alias="sermitsiaq" data-section="erhverv" data-instance="2336218" itemscope="" data-k5a-isslot="true">
    
    <div class="content bg-quaternary color_mobile_bg-quaternary border-bg-quaternary mobile_border-bg-quaternary border_width_14 border_width_mobile_14 hasContentPadding mobile-hasContentPadding hasBorder mobile-hasBorder" style="">
        
        <a itemprop="url" class="" href="/erhverv/trump-oger-interessen-for-gronland/2336218" data-k5a-url="https://www.sermitsiaq.ag/a/2336218" rel="">


        <div class="media ">
                

                <figure data-element-guid="d53115ce-2f55-497f-8a91-4cb3d9e96e8b" class="">
    <div class="img fullwidthTarget">
        <picture>
            <source srcset="https://image.sermitsiaq.ag/2337277.webp?imageId=2337277&amp;width=1058&amp;height=688&amp;format=webp" width="529" height="344" media="(min-width: 768px)" type="image/webp">    
            <img src="https://image.sermitsiaq.ag/2337277.webp?imageId=2337277&amp;width=960&amp;height=624&amp;format=jpg" width="480" height="312" title="Trump øger interessen for Grønland" alt="" loading="lazy" style="">
        </picture>        
            </div>
    
</figure>

                
                
                
                
                
                
                
            
            <div class="floatingText">

                <div class="labels">
                </div>
            </div>
            
<div class="paywallLabel  "><span class="fi-plus"></span> </div>

        </div>

<div class="paywallLabel  "><span class="fi-plus"></span> </div>

        
            <h2 itemprop="headline" class="headline t38 tm30 white color_mobile_white" style="">Trump øger interessen for Grønland
</h2>

        




        </a>

        <time itemprop="datePublished" datetime="2026-01-30T10:41:19+01:00"></time>
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
print("Content Classes:")
print("=" * 80)
print(f"content_classes: {result.get('content_classes')}")
print()

# Check nếu có bg-quaternary
if result.get('content_classes') and 'bg-quaternary' in result['content_classes']:
    print("✅ SUCCESS: bg-quaternary được crawl đúng!")
else:
    print("❌ FAILED: bg-quaternary KHÔNG được crawl!")

print()
print("=" * 80)
print("Full content_classes:")
print("=" * 80)
print(result.get('content_classes', 'None'))

