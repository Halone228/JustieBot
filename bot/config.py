from toml import load, dump


class TOMLConfig:
    def __init__(self, path: str):
        self.path = path
        self.config = load(self.path)

    def save_config(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            dump(self.config, f)

    def __getitem__(self, item):
        return self.config[item]


config = TOMLConfig(path='./config.toml')
