import pstats
from pstats import SortKey

def export_profile_to_text():
    with open("profile.txt", "w", encoding="utf-8") as f:
        stats = pstats.Stats("profile.prof", stream=f)
        stats.strip_dirs()
        stats.sort_stats(SortKey.TIME)
        stats.print_stats(300)

if __name__ == "__main__":
    export_profile_to_text()
