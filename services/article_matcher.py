"""
Service để match articles giữa các ngôn ngữ (DK và KL)
"""
from database import Article, db
from urllib.parse import urlparse


def match_articles_by_element_guid(dk_article, kl_articles):
    """
    Match DK article với KL article qua element_guid
    
    Args:
        dk_article: Article object với language='da'
        kl_articles: List of Article objects với language='kl'
    
    Returns:
        Matching KL article hoặc None
    """
    if not dk_article.element_guid:
        return None
    
    for kl_article in kl_articles:
        if kl_article.element_guid == dk_article.element_guid:
            return kl_article
    
    return None


def match_articles_by_url(dk_article, kl_articles):
    """
    Match DK article với KL article qua published_url
    
    Args:
        dk_article: Article object với language='da'
        kl_articles: List of Article objects với language='kl'
    
    Returns:
        Matching KL article hoặc None
    """
    if not dk_article.published_url:
        return None
    
    # Parse DK URL
    dk_url = urlparse(dk_article.published_url)
    dk_path = dk_url.path
    
    # Convert DK domain to KL domain
    # https://www.sermitsiaq.ag/... -> https://kl.sermitsiaq.ag/...
    kl_domain = dk_url.netloc.replace('www.sermitsiaq.ag', 'kl.sermitsiaq.ag')
    if kl_domain == dk_url.netloc:
        kl_domain = 'kl.sermitsiaq.ag'
    
    for kl_article in kl_articles:
        if not kl_article.published_url:
            continue
        
        kl_url = urlparse(kl_article.published_url)
        
        # Match nếu path giống nhau
        if kl_url.path == dk_path:
            return kl_article
        
        # Hoặc match nếu domain là kl.sermitsiaq.ag và path giống
        if kl_url.netloc == kl_domain and kl_url.path == dk_path:
            return kl_article
    
    return None


def match_articles_by_instance(dk_article, kl_articles):
    """
    Match DK article với KL article qua instance ID
    
    Args:
        dk_article: Article object với language='da'
        kl_articles: List of Article objects với language='kl'
    
    Returns:
        Matching KL article hoặc None
    """
    if not dk_article.instance:
        return None
    
    for kl_article in kl_articles:
        if kl_article.instance == dk_article.instance:
            return kl_article
    
    return None


def link_articles(dk_article, kl_article):
    """
    Link DK và KL articles bằng cách set canonical_id
    
    Args:
        dk_article: Article object với language='da'
        kl_article: Article object với language='kl'
    
    Returns:
        True nếu link thành công, False nếu không
    """
    try:
        # DK article là canonical (gốc)
        # KL article link đến DK
        kl_article.canonical_id = dk_article.id
        kl_article.original_language = 'da'
        
        db.session.commit()
        print(f"   ✅ Linked KL article {kl_article.id} to DK article {dk_article.id}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Failed to link articles: {e}")
        return False


def match_and_link_articles(dk_articles, kl_articles):
    """
    Match và link DK articles với KL articles
    
    Args:
        dk_articles: List of Article objects với language='da'
        kl_articles: List of Article objects với language='kl'
    
    Returns:
        dict: Statistics về matching
    """
    matched_count = 0
    unmatched_dk = []
    unmatched_kl = []
    
    print(f"\n🔗 Matching {len(dk_articles)} DK articles with {len(kl_articles)} KL articles...")
    
    for dk_article in dk_articles:
        # Try matching by element_guid first (most reliable)
        kl_article = match_articles_by_element_guid(dk_article, kl_articles)
        
        # Try matching by URL if element_guid doesn't match
        if not kl_article:
            kl_article = match_articles_by_url(dk_article, kl_articles)
        
        # Try matching by instance if URL doesn't match
        if not kl_article:
            kl_article = match_articles_by_instance(dk_article, kl_articles)
        
        if kl_article:
            if link_articles(dk_article, kl_article):
                matched_count += 1
                # Remove from kl_articles list to avoid duplicate matching
                kl_articles.remove(kl_article)
        else:
            unmatched_dk.append(dk_article)
    
    unmatched_kl = kl_articles
    
    print(f"\n✅ Matching completed:")
    print(f"   - Matched: {matched_count}")
    print(f"   - Unmatched DK: {len(unmatched_dk)}")
    print(f"   - Unmatched KL: {len(unmatched_kl)}")
    
    return {
        'matched_count': matched_count,
        'unmatched_dk': unmatched_dk,
        'unmatched_kl': unmatched_kl
    }

