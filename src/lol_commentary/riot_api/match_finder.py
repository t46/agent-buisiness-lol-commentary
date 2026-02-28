from datetime import datetime, timedelta

from .client import RiotAPIClient


class MatchFinder:
    def __init__(self, client: RiotAPIClient):
        self.client = client

    def find_match(
        self,
        player_names: list[str],
        upload_date: datetime,
        tag_line_candidates: list[str] | None = None,
    ) -> str | None:
        """Find a match ID by cross-referencing player names and upload date.

        Searches match history of each player within +/-7 days of upload_date,
        then checks if at least 2 of the given player names appear in a match.
        """
        if tag_line_candidates is None:
            tag_line_candidates = ["JP1", "jp1"]

        for name in player_names:
            for tag in tag_line_candidates:
                try:
                    account = self.client.get_account_by_riot_id(name, tag)
                    puuid = account["puuid"]

                    start_time = int((upload_date - timedelta(days=7)).timestamp())
                    end_time = int((upload_date + timedelta(days=1)).timestamp())
                    matches = self.client.get_match_list(
                        puuid, start_time=start_time, end_time=end_time
                    )

                    for match_id in matches:
                        match_info = self.client.get_match(match_id)
                        match_names = {
                            p.riot_id_game_name
                            for p in match_info.participants
                            if p.riot_id_game_name
                        }
                        overlap = len(set(player_names) & match_names)
                        if overlap >= 2:
                            return match_id
                except Exception:
                    continue

        return None
