#!/usr/bin/env python3
"""
Script để kiểm tra tại sao article match với query
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
import re

def check_article_match(article_id, search_query):
    """Kiểm tra tại sao article match với query"""
    with app.app_context():
        article = Article.query.get(article_id)
        
        if not article:
            print(f"❌ Không tìm thấy article ID: {article_id}")
            return
        
        print(f"\n{'='*80}")
        print(f"📰 Article ID: {article.id}")
        print(f"{'='*80}")
        print(f"\n📋 Thông tin cơ bản:")
        print(f"   Title: {article.title}")
        print(f"   Language: {article.language}")
        print(f"   Section: {article.section}")
        print(f"   Published URL: {article.published_url}")
        
        # Tokenize search query
        words = []
        for w in re.split(r'\s+', search_query):
            w = w.strip()
            w = re.sub(r'[:;,.!?]+$', '', w)
            if len(w) >= 2:
                words.append(w.lower())
        
        print(f"\n🔍 Search Query Analysis:")
        print(f"   Query: {search_query}")
        print(f"   Tokenized words: {words}")
        print(f"   Total words: {len(words)}")
        print(f"   Required matches (50%): {len(words) // 2 if len(words) >= 4 else len(words)}")
        
        # Check matches in different fields
        print(f"\n🔎 Matching Analysis:")
        
        matched_words = []
        
        # Check title
        if article.title:
            title_lower = article.title.lower()
            title_matches = [w for w in words if w in title_lower]
            if title_matches:
                matched_words.extend(title_matches)
                print(f"   ✅ Title matches: {title_matches}")
                # Show context
                for word in title_matches:
                    idx = title_lower.find(word)
                    context = article.title[max(0, idx-30):idx+len(word)+30]
                    print(f"      '{word}' found at: ...{context}...")
            else:
                print(f"   ❌ Title: No matches")
        
        # Check excerpt
        if article.excerpt:
            excerpt_lower = article.excerpt.lower()
            excerpt_matches = [w for w in words if w in excerpt_lower and w not in matched_words]
            if excerpt_matches:
                matched_words.extend(excerpt_matches)
                print(f"   ✅ Excerpt matches: {excerpt_matches}")
                # Show context
                for word in excerpt_matches:
                    idx = excerpt_lower.find(word)
                    context = article.excerpt[max(0, idx-50):idx+len(word)+50]
                    print(f"      '{word}' found at: ...{context}...")
            else:
                print(f"   ❌ Excerpt: No matches")
        else:
            print(f"   ⚠️  Excerpt: NULL or empty")
        
        # Check content
        if article.content:
            content_lower = article.content.lower()
            content_matches = [w for w in words if w in content_lower and w not in matched_words]
            if content_matches:
                matched_words.extend(content_matches)
                print(f"   ✅ Content matches: {content_matches[:10]}...")  # Limit to 10
                # Show context for first match
                if content_matches:
                    word = content_matches[0]
                    idx = content_lower.find(word)
                    context = article.content[max(0, idx-100):idx+len(word)+100]
                    print(f"      First '{word}' found at: ...{context}...")
            else:
                print(f"   ❌ Content: No matches")
        else:
            print(f"   ⚠️  Content: NULL or empty")
        
        # Check tags
        if article.tags:
            tags_str = ' '.join(article.tags).lower() if isinstance(article.tags, list) else str(article.tags).lower()
            tag_matches = [w for w in words if w in tags_str and w not in matched_words]
            if tag_matches:
                matched_words.extend(tag_matches)
                print(f"   ✅ Tags matches: {tag_matches}")
            else:
                print(f"   ❌ Tags: No matches")
        else:
            print(f"   ⚠️  Tags: NULL or empty")
        
        # Check ArticleDetail.content_blocks
        article_details = ArticleDetail.query.filter_by(published_url=article.published_url).all()
        if article_details:
            for detail in article_details:
                print(f"\n   📚 ArticleDetail (language: {detail.language}):")
                if detail.content_blocks:
                    # Convert content_blocks to string for searching
                    content_blocks_str = str(detail.content_blocks).lower()
                    detail_matches = [w for w in words if w in content_blocks_str and w not in matched_words]
                    if detail_matches:
                        matched_words.extend(detail_matches)
                        print(f"      ✅ Content blocks matches: {detail_matches[:10]}...")
                        # Try to find which block contains the match
                        for block in detail.content_blocks:
                            if isinstance(block, dict):
                                block_text = str(block.get('text', '') + ' ' + str(block.get('html', ''))).lower()
                                block_matches = [w for w in words if w in block_text]
                                if block_matches:
                                    print(f"         Block type '{block.get('type', 'unknown')}' matches: {block_matches}")
                                    # Show context
                                    for word in block_matches[:2]:  # Limit to 2 words
                                        text = block.get('text', '') or block.get('html', '')
                                        if text:
                                            text_lower = text.lower()
                                            idx = text_lower.find(word)
                                            if idx >= 0:
                                                context = text[max(0, idx-50):idx+len(word)+50]
                                                print(f"            '{word}' in block: ...{context}...")
                    else:
                        print(f"      ❌ Content blocks: No matches")
                else:
                    print(f"      ⚠️  Content blocks: NULL or empty")
        else:
            print(f"\n   ⚠️  ArticleDetail: Not found")
        
        # Summary
        unique_matched_words = list(set(matched_words))
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY:")
        print(f"{'='*80}")
        print(f"   Total search words: {len(words)}")
        print(f"   Matched words: {len(unique_matched_words)}")
        print(f"   Matched words list: {unique_matched_words}")
        print(f"   Required matches (50%): {len(words) // 2 if len(words) >= 4 else len(words)}")
        
        if len(unique_matched_words) >= (len(words) // 2 if len(words) >= 4 else len(words)):
            print(f"   ✅ PASSES threshold ({len(unique_matched_words)} >= {len(words) // 2 if len(words) >= 4 else len(words)})")
        else:
            print(f"   ❌ FAILS threshold ({len(unique_matched_words)} < {len(words) // 2 if len(words) >= 4 else len(words)})")
        
        # Show which words didn't match
        unmatched_words = [w for w in words if w not in unique_matched_words]
        if unmatched_words:
            print(f"\n   ❌ Unmatched words: {unmatched_words}")

if __name__ == '__main__':
    # Article ID from debug output
    article_id = 30709
    search_query = "Centrale nøgletal: Fremtiden ser dyster ud"
    
    check_article_match(article_id, search_query)
