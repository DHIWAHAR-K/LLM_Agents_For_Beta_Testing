"""
Figure Generation Script for NeurIPS Paper

Generates publication-quality figures from experimental database.
All figures are saved in both PDF (vector) and PNG (raster) formats.

Usage:
    python experiments/generate_figures.py
"""

import sqlite3
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# NeurIPS style configuration
NEURIPS_STYLE = {
    'figure.figsize': (6, 4),
    'figure.dpi': 300,
    'font.size': 10,
    'font.family': 'serif',
    'font.serif': ['Times', 'Computer Modern Roman', 'DejaVu Serif'],
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'legend.frameon': True,
    'legend.fancybox': True,
    'legend.shadow': False,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.5,
    'patch.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
}

# Colorblind-friendly palette
COLORS = {
    'primary': '#2E86AB',      # Blue
    'secondary': '#A23B72',    # Purple
    'success': '#06A77D',     # Green
    'warning': '#F18F01',     # Orange
    'danger': '#C73E1D',       # Red
    'neutral': '#6C757D',      # Gray
    'light_blue': '#7FB3D3',
    'light_green': '#7FBC8C',
    'light_orange': '#F4A261',
}

# Apply style
plt.rcParams.update(NEURIPS_STYLE)
sns.set_style("whitegrid", {'axes.spines.top': False, 'axes.spines.right': False})


class DataExtractor:
    """Extracts data from database for figure generation"""
    
    def __init__(self, db_path: str = "experiments/results/experiments.db"):
        self.db_path = db_path
    
    def get_action_distribution(self) -> Dict:
        """Get action type distribution and success rates"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                action_type,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM turns
            GROUP BY action_type
            ORDER BY total DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        data = {
            'types': [r[0] for r in results],
            'total': [r[1] for r in results],
            'successful': [r[2] for r in results],
            'success_rates': [100.0 * r[2] / r[1] if r[1] > 0 else 0 for r in results]
        }
        
        return data
    
    def get_persona_performance(self) -> Dict:
        """Get persona performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.persona_name,
                COUNT(DISTINCT r.id) as runs,
                AVG(m.task_success_rate) as avg_success,
                AVG(m.total_turns) as avg_turns,
                AVG(m.avg_latency_seconds) as avg_latency
            FROM runs r
            JOIN metrics m ON r.id = m.run_id
            WHERE r.persona_name IS NOT NULL
            GROUP BY r.persona_name
            ORDER BY avg_success DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        data = {
            'personas': [r[0] for r in results],
            'runs': [r[1] for r in results],
            'success_rates': [r[2] for r in results],
            'avg_turns': [r[3] for r in results],
            'avg_latency': [r[4] for r in results]
        }
        
        return data
    
    def get_multi_agent_scaling(self) -> Dict:
        """Get multi-agent committee scaling results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.num_agents,
                COUNT(DISTINCT r.id) as runs,
                AVG(m.task_success_rate) as avg_success,
                AVG(m.avg_committee_agreement) as avg_agreement,
                AVG(m.consensus_strength) as avg_consensus
            FROM runs r
            JOIN metrics m ON r.id = m.run_id
            WHERE r.num_agents IS NOT NULL
            GROUP BY r.num_agents
            ORDER BY r.num_agents
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        data = {
            'num_agents': [r[0] for r in results],
            'runs': [r[1] for r in results],
            'success_rates': [r[2] for r in results],
            'agreement': [r[3] if r[3] else 0 for r in results],
            'consensus': [r[4] if r[4] else 0 for r in results]
        }
        
        return data
    
    def get_baseline_comparison(self) -> Dict:
        """Get baseline comparison data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get WebShop results
        cursor.execute("""
            SELECT AVG(m.task_success_rate)
            FROM runs r
            JOIN metrics m ON r.id = m.run_id
            JOIN experiments e ON r.experiment_id = e.id
            WHERE e.name = 'webshop_task_success'
        """)
        webshop_result = cursor.fetchone()[0] or 0
        
        # Get OWASP results
        cursor.execute("""
            SELECT AVG(m.task_success_rate)
            FROM runs r
            JOIN metrics m ON r.id = m.run_id
            JOIN experiments e ON r.experiment_id = e.id
            WHERE e.name = 'owasp_juice_shop_security_testing'
        """)
        owasp_result = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Published baselines
        baselines = {
            'webshop': {
                'ours': webshop_result,
                'gpt3': 50.1,
                'rl_agent': 29.0,
                'human': 65.0  # Midpoint of 60-70% range
            },
            'owasp': {
                'ours': owasp_result,
                'commercial': 50.0  # Midpoint of 40-60% range
            }
        }
        
        return baselines
    
    def get_scenario_performance(self) -> Dict:
        """Get scenario performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.scenario_name,
                COUNT(DISTINCT r.id) as runs,
                AVG(m.task_success_rate) as avg_success
            FROM runs r
            JOIN metrics m ON r.id = m.run_id
            WHERE r.scenario_name IS NOT NULL
            GROUP BY r.scenario_name
            ORDER BY avg_success DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        data = {
            'scenarios': [r[0] for r in results],
            'runs': [r[1] for r in results],
            'success_rates': [r[2] for r in results]
        }
        
        return data


class FigureGenerator:
    """Generates publication-quality figures for NeurIPS paper"""
    
    def __init__(self, db_path: str = "experiments/results/experiments.db", 
                 output_dir: str = "paper/figures"):
        self.extractor = DataExtractor(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_figure(self, fig, filename: str, dpi: int = 300):
        """Save figure in both PDF and PNG formats"""
        pdf_path = self.output_dir / f"{filename}.pdf"
        png_path = self.output_dir / f"{filename}.png"
        
        fig.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=dpi)
        fig.savefig(png_path, format='png', bbox_inches='tight', dpi=dpi)
        print(f"✓ Saved {filename}.pdf and {filename}.png")
        plt.close(fig)
    
    def generate_action_distribution(self):
        """Generate action distribution bar chart"""
        data = self.extractor.get_action_distribution()
        
        fig, ax = plt.subplots(figsize=(6, 4))
        
        x = np.arange(len(data['types']))
        width = 0.6
        
        # Create bars
        bars = ax.bar(x, data['success_rates'], width, 
                     color=COLORS['primary'], alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Add value labels on bars
        for i, (bar, rate) in enumerate(zip(bars, data['success_rates'])):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{rate:.1f}%',
                   ha='center', va='bottom', fontsize=9)
        
        # Customize axes
        ax.set_xlabel('Action Type', fontweight='bold')
        ax.set_ylabel('Success Rate (%)', fontweight='bold')
        ax.set_title('Action Success Rates by Type', fontweight='bold', pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(data['types'], rotation=0)
        ax.set_ylim(-15, 110)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add total count annotations with better spacing
        for i, (type_name, total) in enumerate(zip(data['types'], data['total'])):
            ax.text(i, -8, f'n={total}', ha='center', va='top', fontsize=8, style='italic')
        
        plt.tight_layout()
        self.save_figure(fig, 'action_distribution')
    
    def generate_baseline_comparison(self):
        """Generate baseline comparison bar chart"""
        data = self.extractor.get_baseline_comparison()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        # WebShop comparison
        webshop_data = data['webshop']
        webshop_systems = ['GPT-3\n(Baseline)', 'RL Agent\n(Baseline)', 'Human\n(Reference)', 'Our\nMulti-Agent']
        webshop_values = [webshop_data['gpt3'], webshop_data['rl_agent'], 
                         webshop_data['human'], webshop_data['ours']]
        webshop_colors = [COLORS['neutral'], COLORS['neutral'], COLORS['neutral'], COLORS['success']]
        
        bars1 = ax1.bar(webshop_systems, webshop_values, color=webshop_colors, 
                       alpha=0.8, edgecolor='black', linewidth=0.5)
        
        for bar, val in zip(bars1, webshop_values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{val:.1f}%',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax1.set_ylabel('Task Success Rate (%)', fontweight='bold')
        ax1.set_title('WebShop Benchmark Comparison', fontweight='bold', pad=10)
        ax1.set_ylim(0, 85)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add improvement annotation
        improvement = webshop_data['ours'] - webshop_data['gpt3']
        ax1.annotate(f'+{improvement:.1f}pp', 
                    xy=(3, webshop_data['ours']), 
                    xytext=(3, webshop_data['ours'] + 5),
                    arrowprops=dict(arrowstyle='->', color=COLORS['success'], lw=2),
                    fontsize=10, fontweight='bold', color=COLORS['success'],
                    ha='center')
        
        # OWASP comparison
        owasp_data = data['owasp']
        owasp_systems = ['Commercial\nTools', 'Our\nMulti-Agent']
        owasp_values = [owasp_data['commercial'], owasp_data['ours']]
        owasp_colors = [COLORS['neutral'], COLORS['success']]
        
        bars2 = ax2.bar(owasp_systems, owasp_values, color=owasp_colors,
                       alpha=0.8, edgecolor='black', linewidth=0.5)
        
        for bar, val in zip(bars2, owasp_values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{val:.1f}%',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax2.set_ylabel('Task Success Rate (%)', fontweight='bold')
        ax2.set_title('OWASP Juice Shop Comparison', fontweight='bold', pad=10)
        ax2.set_ylim(0, 90)
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        self.save_figure(fig, 'baseline_comparison')
    
    def generate_persona_results(self):
        """Generate persona performance heatmap/bar chart"""
        data = self.extractor.get_persona_performance()
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Sort by success rate
        sorted_indices = np.argsort(data['success_rates'])[::-1]
        personas = [data['personas'][i] for i in sorted_indices]
        success_rates = [data['success_rates'][i] for i in sorted_indices]
        
        # Create horizontal bar chart
        y_pos = np.arange(len(personas))
        bars = ax.barh(y_pos, success_rates, color=COLORS['primary'], alpha=0.8, 
                      edgecolor='black', linewidth=0.5)
        
        # Add value labels
        for i, (bar, rate) in enumerate(zip(bars, success_rates)):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2.,
                   f'{rate:.1f}%',
                   ha='left', va='center', fontsize=9, fontweight='bold')
        
        # Customize axes
        ax.set_yticks(y_pos)
        ax.set_yticklabels([p.replace('_', ' ').title() for p in personas])
        ax.set_xlabel('Task Success Rate (%)', fontweight='bold')
        ax.set_title('Persona Performance Comparison', fontweight='bold', pad=10)
        ax.set_xlim(0, 105)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        self.save_figure(fig, 'persona_results')
    
    def generate_multi_agent_scaling(self):
        """Generate multi-agent scaling line plot"""
        data = self.extractor.get_multi_agent_scaling()
        
        if len(data['num_agents']) < 2:
            print("⚠ Insufficient data for multi-agent scaling plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        # Success rate plot
        ax1.plot(data['num_agents'], data['success_rates'], 
                marker='o', markersize=8, linewidth=2, color=COLORS['success'],
                label='Task Success Rate', markerfacecolor=COLORS['success'],
                markeredgecolor='black', markeredgewidth=1)
        
        # Add value labels
        for x, y in zip(data['num_agents'], data['success_rates']):
            ax1.annotate(f'{y:.1f}%', (x, y), textcoords="offset points",
                        xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
        
        ax1.set_xlabel('Committee Size (Number of Agents)', fontweight='bold')
        ax1.set_ylabel('Task Success Rate (%)', fontweight='bold')
        ax1.set_title('Task Success vs Committee Size', fontweight='bold', pad=10)
        ax1.set_xticks(data['num_agents'])
        ax1.set_ylim(70, 105)
        ax1.grid(alpha=0.3, linestyle='--')
        ax1.legend(loc='lower right')
        
        # Agreement plot
        ax2.plot(data['num_agents'], data['agreement'], 
                marker='s', markersize=8, linewidth=2, color=COLORS['primary'],
                label='Committee Agreement', markerfacecolor=COLORS['primary'],
                markeredgecolor='black', markeredgewidth=1)
        
        # Add value labels
        for x, y in zip(data['num_agents'], data['agreement']):
            if y > 0:  # Only label non-zero values
                ax2.annotate(f'{y:.0f}%', (x, y), textcoords="offset points",
                            xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
        
        ax2.set_xlabel('Committee Size (Number of Agents)', fontweight='bold')
        ax2.set_ylabel('Committee Agreement (%)', fontweight='bold')
        ax2.set_title('Committee Agreement vs Committee Size', fontweight='bold', pad=10)
        ax2.set_xticks(data['num_agents'])
        ax2.set_ylim(-5, 105)
        ax2.grid(alpha=0.3, linestyle='--')
        ax2.legend(loc='lower right')
        
        plt.tight_layout()
        self.save_figure(fig, 'multi_agent_scaling')
    
    def generate_voting_protocol(self):
        """Generate voting protocol flowchart (algorithm diagram)"""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.axis('off')
        
        # Define positions
        y_start = 0.9
        y_step = 0.25
        box_height = 0.15
        box_width = 0.3
        
        # Round 1
        round1_box = FancyBboxPatch((0.1, y_start), box_width, box_height,
                                   boxstyle="round,pad=0.02", 
                                   facecolor=COLORS['light_blue'], 
                                   edgecolor='black', linewidth=1.5)
        ax.add_patch(round1_box)
        ax.text(0.25, y_start + box_height/2, 'Round 1:\nIndependent\nProposals', 
               ha='center', va='center', fontsize=10, fontweight='bold')
        
        # Arrow 1
        ax.arrow(0.4, y_start + box_height/2, 0.15, 0, 
               head_width=0.02, head_length=0.02, fc='black', ec='black', lw=1.5)
        
        # Round 2
        round2_box = FancyBboxPatch((0.55, y_start), box_width, box_height,
                                   boxstyle="round,pad=0.02",
                                   facecolor=COLORS['light_green'],
                                   edgecolor='black', linewidth=1.5)
        ax.add_patch(round2_box)
        ax.text(0.7, y_start + box_height/2, 'Round 2:\nDiscussion &\nRefinement', 
               ha='center', va='center', fontsize=10, fontweight='bold')
        
        # Arrow 2
        ax.arrow(0.85, y_start + box_height/2, 0.15, 0,
               head_width=0.02, head_length=0.02, fc='black', ec='black', lw=1.5)
        
        # Round 3
        round3_box = FancyBboxPatch((1.0, y_start), box_width, box_height,
                                   boxstyle="round,pad=0.02",
                                   facecolor=COLORS['light_orange'],
                                   edgecolor='black', linewidth=1.5)
        ax.add_patch(round3_box)
        ax.text(1.15, y_start + box_height/2, 'Round 3:\nConsensus\nVote', 
               ha='center', va='center', fontsize=10, fontweight='bold')
        
        # Agent details (below main flow)
        agent_y = y_start - 0.35
        for i, agent_num in enumerate([1, 2, 3, 4]):
            x_pos = 0.1 + i * 0.25
            agent_box = FancyBboxPatch((x_pos, agent_y), 0.2, 0.12,
                                     boxstyle="round,pad=0.01",
                                     facecolor='white',
                                     edgecolor=COLORS['primary'], linewidth=1)
            ax.add_patch(agent_box)
            ax.text(x_pos + 0.1, agent_y + 0.06, f'Agent {agent_num}',
                   ha='center', va='center', fontsize=9)
        
        # Round 1 details
        detail_y = agent_y - 0.2
        ax.text(0.25, detail_y, 'Each agent proposes\naction independently',
               ha='center', va='top', fontsize=9, style='italic',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        # Round 2 details
        ax.text(0.7, detail_y, 'Agents see all proposals\nand refine their choices',
               ha='center', va='top', fontsize=9, style='italic',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        # Round 3 details
        ax.text(1.15, detail_y, 'Confidence-weighted\nvote selects action',
               ha='center', va='top', fontsize=9, style='italic',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        ax.set_xlim(0, 1.4)
        ax.set_ylim(0, 1)
        ax.set_title('Three-Round Voting Protocol', fontsize=12, fontweight='bold', pad=20)
        
        plt.tight_layout()
        self.save_figure(fig, 'voting_protocol')
    
    def generate_architecture(self):
        """Generate system architecture diagram"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axis('off')
        
        # Main components
        components = [
            ('Multi-Agent\nCommittee', 0.2, 0.8, COLORS['primary']),
            ('Browser\nAdapter', 0.5, 0.8, COLORS['secondary']),
            ('Application\nUnder Test', 0.8, 0.8, COLORS['success']),
            ('Storage &\nMetrics', 0.2, 0.4, COLORS['warning']),
            ('Statistical\nAnalysis', 0.5, 0.4, COLORS['neutral']),
            ('Figure\nGeneration', 0.8, 0.4, COLORS['light_blue']),
        ]
        
        for name, x, y, color in components:
            box = FancyBboxPatch((x-0.08, y-0.1), 0.16, 0.2,
                               boxstyle="round,pad=0.02",
                               facecolor=color, alpha=0.7,
                               edgecolor='black', linewidth=1.5)
            ax.add_patch(box)
            ax.text(x, y, name, ha='center', va='center', 
                   fontsize=9, fontweight='bold')
        
        # Arrows
        arrows = [
            ((0.2, 0.7), (0.5, 0.7)),  # Committee -> Browser
            ((0.5, 0.7), (0.8, 0.7)),  # Browser -> AUT
            ((0.5, 0.6), (0.2, 0.5)),   # Browser -> Storage
            ((0.2, 0.3), (0.5, 0.3)),  # Storage -> Analysis
            ((0.5, 0.3), (0.8, 0.3)),  # Analysis -> Figures
        ]
        
        for (x1, y1), (x2, y2) in arrows:
            ax.arrow(x1, y1, x2-x1, y2-y1,
                   head_width=0.015, head_length=0.015,
                   fc='black', ec='black', lw=1.5)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('Multi-Agent Testing Framework Architecture', 
                    fontsize=12, fontweight='bold', pad=20)
        
        plt.tight_layout()
        self.save_figure(fig, 'architecture')
    
    def generate_all(self):
        """Generate all figures"""
        print("Generating figures for NeurIPS paper...")
        print("=" * 60)
        
        self.generate_action_distribution()
        self.generate_baseline_comparison()
        self.generate_persona_results()
        self.generate_multi_agent_scaling()
        self.generate_voting_protocol()
        self.generate_architecture()
        
        print("=" * 60)
        print("✓ All figures generated successfully!")
        print(f"Figures saved to: {self.output_dir}")


if __name__ == "__main__":
    generator = FigureGenerator()
    generator.generate_all()

