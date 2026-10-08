"""Estado independiente de tablas originales y datasets derivados, sin persistencia."""
from dataclasses import dataclass, field
from .cleaning import History
from .profiling import metrics
from .quality import assess


@dataclass
class Dataset:
    name: str
    history: History
    source: str
    size: int = 0
    lineage: dict = field(default_factory=dict)


class Workspace:
    def __init__(self):
        self.datasets = {}
        self.active = None
        self._next = 1

    def add(self, df, name, source='', size=0, lineage=None):
        if df.size + sum(d.history.current.size for d in self.datasets.values()) > 4_000_000:
            raise ValueError('La sesión supera cuatro millones de celdas, incluidos datasets derivados.')
        if len(self.datasets) >= 40:
            raise ValueError('Máximo 40 datasets por sesión. Iniciá una nueva sesión para liberar memoria.')
        key = f'dataset_{self._next}'
        self._next += 1
        self.datasets[key] = Dataset(name, History(df), source, size, lineage or {})
        self.active = key
        return key

    def select(self, key):
        if key not in self.datasets:
            raise ValueError('Dataset inexistente.')
        self.active = key
        return self.datasets[key]

    def frames(self):
        return {key: dataset.history.current for key, dataset in self.datasets.items()}

    def summary(self):
        rows = []
        for key, dataset in self.datasets.items():
            df = dataset.history.current
            m = metrics(df)
            score = assess(df)['score']
            rows.append({'Dataset': dataset.name, 'Origen': dataset.source, 'Filas': m['Filas'],
                         'Columnas': m['Columnas'], 'Tipos': ', '.join(sorted(set(df.dtypes.astype(str)))),
                         'Faltantes': m['Faltantes'], 'Duplicados': m['Duplicados'],
                         'Índice orientativo': score,
                         'Estado': 'Revisar' if score < 95 else 'Sin alertas en el índice',
                         'Transformaciones': len(dataset.history.records)})
        return rows
