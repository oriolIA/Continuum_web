"""
Layout Design - Posicionament òptim de turbines

Features:
- Posicionament de turbines
- Optimització amb Algorismes Genètics
- Compliance amb restriccions (distància mínima, terreny, etc.)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np
import random


@dataclass
class LayoutConfig:
    """Configuració pel disseny de layout"""
    n_turbines: int
    min_distance: float = 500  # m entre turbines
    boundary_polygon: Optional[np.ndarray] = None  # shape (N, 2)
    min_x: Optional[float] = None
    max_x: Optional[float] = None
    min_y: Optional[float] = None
    max_y: Optional[float] = None


@dataclass
class Layout:
    """Disseny d'un parc eòlic"""
    name: str
    turbines: List[Tuple[float, float]]  # (x, y) per turbina
    fitness: float = 0.0
    
    def to_numpy(self) -> np.ndarray:
        return np.array(self.turbines)


class LayoutGA:
    """
    Algorisme Genètic per optimització de layout
    
    Objectiu: Maximitzar producció (minimitzar wake losses)
    """
    
    def __init__(
        self,
        config: LayoutConfig,
        wind_rose: np.ndarray,  # shape (n_sectors,)
        wake_model,
        population_size: int = 100,
        n_generations: int = 200,
        mutation_rate: float = 0.1
    ):
        self.config = config
        self.wind_rose = wind_rose
        self.wake_model = wake_model
        self.population_size = population_size
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
    
    def _create_random_layout(self) -> Layout:
        """Crea un layout aleatori vàlid"""
        turbines = []
        
        for _ in range(self.config.n_turbines):
            max_attempts = 100
            for _ in range(max_attempts):
                x = random.uniform(self.config.min_x, self.config.max_x)
                y = random.uniform(self.config.min_y, self.config.max_y)
                
                # Verificar distància mínima
                valid = True
                for tx, ty in turbines:
                    dist = np.sqrt((x - tx)**2 + (y - ty)**2)
                    if dist < self.config.min_distance:
                        valid = False
                        break
                
                if valid:
                    turbines.append((x, y))
                    break
            
            # Si no troba posició vàlida, afegeix igualment
            if len(turbines) <= _:
                turbines.append((x, y))
        
        return Layout(name="random", turbines=turbines)
    
    def _fitness(self, layout: Layout) -> float:
        """
        Calcula la fitness del layout
        Més alta = millor layout
        """
        # Simular pèrdues de wake amb cada sector
        total_loss = 0.0
        
        for sector, wind_freq in enumerate(self.wind_rose):
            direction = sector * 30  # 12 sectors de 30°
            
            # Calcular pèrdues per a cada turbina
            sector_loss = 0.0
            for i, (x, y) in enumerate(layout.turbines):
                for j, (ox, oy) in enumerate(layout.turbines):
                    if i != j:
                        dist = np.sqrt((x - ox)**2 + (y - oy)**2)
                        if dist < 2000:  # Només turbines properes afecten
                            deficit = self.wake_model.calculate_deficit(dist, direction)
                            sector_loss += deficit
            
            total_loss += sector_loss * wind_freq
        
        # Fitness = 1 - pèrdues normalitzades
        max_loss = self.config.n_turbines * len(self.wind_rose)
        fitness = 1.0 - (total_loss / max_loss if max_loss > 0 else 0)
        
        return fitness
    
    def _crossover(self, parent1: Layout, parent2: Layout) -> Layout:
        """Crossover de dos layouts"""
        # Interpolació de posicions
        turbines = []
        for i in range(len(parent1.turbines)):
            x = (parent1.turbines[i][0] + parent2.turbines[i][0]) / 2
            y = (parent1.turbines[i][1] + parent2.turbines[i][1]) / 2
            turbines.append((x, y))
        
        return Layout(name="crossover", turbines=turbines)
    
    def _mutate(self, layout: Layout) -> Layout:
        """Mutació d'un layout"""
        turbines = list(layout.turbines)
        
        for i in range(len(turbines)):
            if random.random() < self.mutation_rate:
                # Moure turbina aleatòriament
                x, y = turbines[i]
                x += random.uniform(-100, 100)
                y += random.uniform(-100, 100)
                
                # Mantenir dins dels limits
                x = np.clip(x, self.config.min_x, self.config.max_x)
                y = np.clip(y, self.config.min_y, self.config.max_y)
                
                turbines[i] = (x, y)
        
        return Layout(name="mutated", turbines=turbines)
    
    def optimize(self) -> Layout:
        """
        Executa l'algorisme genètic
        """
        # Inicialitzar població
        population = [self._create_random_layout() for _ in range(self.population_size)]
        
        best_layout = None
        best_fitness = 0.0
        
        for gen in range(self.n_generations):
            # Avaluar fitness
            for layout in population:
                layout.fitness = self._fitness(layout)
                
                if layout.fitness > best_fitness:
                    best_fitness = layout.fitness
                    best_layout = layout
            
            # Selecció (tournament)
            selected = []
            for _ in range(self.population_size):
                candidates = random.sample(population, 5)
                winner = max(candidates, key=lambda x: x.fitness)
                selected.append(winner)
            
            # Reproducció
            new_population = []
            for i in range(0, self.population_size - 1, 2):
                if i + 1 < self.population_size:
                    child = self._crossover(selected[i], selected[i + 1])
                    child = self._mutate(child)
                    new_population.append(child)
            
            population = new_population
            
            if gen % 50 == 0:
                print(f"Gen {gen}: Best fitness = {best_fitness:.4f}")
        
        return best_layout


class LayoutGrid:
    """
    Layout en graella (simplificat)
    """
    
    @staticmethod
    def create(
        n_rows: int,
        n_cols: int,
        spacing_x: float,
        spacing_y: float,
        offset_x: float = 0,
        offset_y: float = 0
    ) -> Layout:
        """Crea layout en graella"""
        turbines = []
        
        for i in range(n_rows):
            for j in range(n_cols):
                x = offset_x + j * spacing_x
                y = offset_y + i * spacing_y
                turbines.append((x, y))
        
        return Layout(name="grid", turbines=turbines)
    
    @staticmethod
    def create_staggered(
        n_rows: int,
        n_cols: int,
        spacing_x: float,
        spacing_y: float,
        offset_x: float = 0,
        offset_y: float = 0
    ) -> Layout:
        """Crea layout en graella estaggerada (més eficient)"""
        turbines = []
        
        for i in range(n_rows):
            for j in range(n_cols):
                x = offset_x + j * spacing_x
                if i % 2 == 1:
                    x += spacing_x / 2  # Estagger
                y = offset_y + i * spacing_y
                turbines.append((x, y))
        
        return Layout(name="staggered", turbines=turbines)


class LayoutOptimizer:
    """
    Optimitzador de layouts amb múltiples mètodes
    """
    
    @staticmethod
    def optimize_grid(
        n_turbines: int,
        area_width: float,
        area_height: float,
        wind_rose: np.ndarray,
        wake_model,
        aspect_ratio: float = 1.5  # width/height ratio
    ) -> Layout:
        """
        Optimitza espaiat de graella
        """
        # Calcular dimensions òptimes
        n_cols = int(np.sqrt(n_turbines / aspect_ratio))
        n_rows = int(np.ceil(n_turbines / n_cols))
        
        spacing_x = area_width / (n_cols + 1)
        spacing_y = area_height / (n_rows + 1)
        spacing = min(spacing_x, spacing_y)
        
        # Provar staggered vs normal
        staggered = LayoutGrid.create_staggered(
            n_rows, n_cols, spacing, spacing * 0.8,
            offset_x=spacing, offset_y=spacing
        )
        
        return staggered
    
    @staticmethod
    def random_search(
        n_turbines: int,
        area_bounds: Tuple[float, float, float, float],  # min_x, max_x, min_y, max_y
        n_iterations: int = 1000,
        wake_model = None,
        wind_rose: np.ndarray = None
    ) -> Layout:
        """
        Cerca aleatòria (simple però efectiva)
        """
        min_x, max_x, min_y, max_y = area_bounds
        
        best_layout = None
        best_fitness = 0.0
        
        for i in range(n_iterations):
            turbines = []
            for j in range(n_turbines):
                x = random.uniform(min_x, max_x)
                y = random.uniform(min_y, max_y)
                turbines.append((x, y))
            
            layout = Layout(name="random_search", turbines=turbines)
            
            # Fitness simple: dispersió (evita turbines massa juntes)
            if len(turbines) > 1:
                avg_dist = 0
                for k in range(len(turbines)):
                    for l in range(k + 1, len(turbines)):
                        d = np.sqrt(
                            (turbines[k][0] - turbines[l][0])**2 +
                            (turbines[k][1] - turbines[l][1])**2
                        )
                        avg_dist += d
                avg_dist /= (n_turbines * (n_turbines - 1) / 2)
                
                # Maximitzar distància mitjana
                layout.fitness = avg_dist / 1000  # Normalitzar
            else:
                layout.fitness = 1.0
            
            if layout.fitness > best_fitness:
                best_fitness = layout.fitness
                best_layout = layout
        
        return best_layout


def calculate_layout_metrics(layout: Layout) -> dict:
    """
    Calcula mètriques d'un layout
    """
    turbines = np.array(layout.turbines)
    n = len(turbines)
    
    # Àrea ocupada
    if n > 0:
        min_x, max_x = turbines[:, 0].min(), turbines[:, 0].max()
        min_y, max_y = turbines[:, 1].min(), turbines[:, 1].max()
        area = (max_x - min_x) * (max_y - min_y)
    else:
        area = 0
    
    # Distàncies
    distances = []
    for i in range(n):
        for j in range(i + 1, n):
            d = np.sqrt(
                (turbines[i][0] - turbines[j][0])**2 +
                (turbines[i][1] - turbines[j][1])**2
            )
            distances.append(d)
    
    return {
        "n_turbines": n,
        "area_m2": area,
        "area_km2": area / 1e6,
        "avg_distance_m": np.mean(distances) if distances else 0,
        "min_distance_m": min(distances) if distances else 0,
        "max_distance_m": max(distances) if distances else 0,
        "density_turbines_km2": n / (area / 1e6) if area > 0 else 0
    }
