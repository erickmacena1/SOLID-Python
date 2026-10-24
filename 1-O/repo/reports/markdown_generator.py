class MarkdownGenerator():
    @classmethod
    def build(cls, repos):
        items = ' '.join(
            f'**ID:** {repo.id} **NAME:** {repo.name} **STARTS:** {repo.stars}\n'
            for repo in repos)
        return f'## REPOS \n\n{items}'