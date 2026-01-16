"""
Utility functions for Flask app
"""

def group_articles_by_row(articles, articles_per_row=2):
    """
    Group articles into rows for grid layout
    
    Args:
        articles: List of article dictionaries
        articles_per_row: Number of articles per row (2 or 3)
    
    Returns:
        List of lists, each inner list contains articles for one row
    """
    if not articles:
        return []
    
    # Calculate grid_size based on articles_per_row
    grid_size = 6 if articles_per_row == 2 else 4
    
    # Set grid_size for each article
    for article in articles:
        if 'grid_size' not in article:
            article['grid_size'] = grid_size
    
    # Group articles into rows
    rows = []
    for i in range(0, len(articles), articles_per_row):
        rows.append(articles[i:i + articles_per_row])
    
    return rows

