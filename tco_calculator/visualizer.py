"""
Visualization module for TCO results.
"""

import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional
from .models import TCOResult


class TCOVisualizer:
    """Create visualizations for TCO analysis."""
    
    @staticmethod
    def plot_comparison(result: TCOResult, show: bool = True) -> plt.Figure:
        """
        Create comprehensive TCO comparison visualization.
        
        Args:
            result: TCOResult object
            show: Whether to display the plot
            
        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            f"TCO Comparison: {result.ev_results.vehicle_name} vs {result.ice_results.vehicle_name}",
            fontsize=16, fontweight='bold'
        )
        
        # 1. Cumulative costs over time
        ax = axes[0, 0]
        years = list(range(result.scenario.years))
        ax.plot(years, result.ev_results.cumulative_costs, marker='o', label='EV', linewidth=2)
        ax.plot(years, result.ice_results.cumulative_costs, marker='s', label='ICE', linewidth=2)
        if result.breakeven_year is not None:
            ax.axvline(x=result.breakeven_year, color='green', linestyle='--', alpha=0.5)
            ax.text(result.breakeven_year, 0, f'Breakeven\nYear {result.breakeven_year}', 
                   ha='center', fontsize=10)
        ax.set_xlabel('Year')
        ax.set_ylabel('Cumulative Cost ($)')
        ax.set_title('Cumulative Cost Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}k'))
        
        # 2. Annual cost breakdown (EV)
        ax = axes[0, 1]
        ev_df = result.ev_results.to_dataframe()
        ev_costs = ev_df[[col for col in ev_df.columns if col not in ['Year', 'Total Cost']]].sum()
        colors = plt.cm.Set3(range(len(ev_costs)))
        ax.pie(ev_costs, labels=ev_costs.index, autopct='%1.1f%%', colors=colors)
        ax.set_title(f'EV Cost Breakdown\nTotal: ${result.ev_results.total_cost:,.0f}')
        
        # 3. Annual cost breakdown (ICE)
        ax = axes[1, 0]
        ice_df = result.ice_results.to_dataframe()
        ice_costs = ice_df[[col for col in ice_df.columns if col not in ['Year', 'Total Cost']]].sum()
        colors = plt.cm.Set3(range(len(ice_costs)))
        ax.pie(ice_costs, labels=ice_costs.index, autopct='%1.1f%%', colors=colors)
        ax.set_title(f'ICE Cost Breakdown\nTotal: ${result.ice_results.total_cost:,.0f}')
        
        # 4. Summary metrics
        ax = axes[1, 1]
        ax.axis('off')
        
        summary_text = f"""
        ECONOMIC ANALYSIS
        
        EV Total Cost:         ${result.ev_results.total_cost:>15,.0f}
        ICE Total Cost:        ${result.ice_results.total_cost:>15,.0f}
        Total Savings (EV):    ${result.total_savings:>15,.0f}
        
        Present Value Analysis
        EV PV Cost:            ${result.ev_results.present_value_cost:>15,.0f}
        ICE PV Cost:           ${result.ice_results.present_value_cost:>15,.0f}
        PV Savings (EV):       ${result.pv_savings:>15,.0f}
        
        Breakeven Year:        {result.breakeven_year or "No breakeven"}
        Analysis Period:       {result.scenario.years} years
        Discount Rate:         {result.scenario.discount_rate*100:.1f}%
        """
        
        ax.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
               verticalalignment='center', bbox=dict(boxstyle='round', 
               facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        if show:
            plt.show()
        
        return fig
    
    @staticmethod
    def plot_annual_costs(result: TCOResult, show: bool = True) -> plt.Figure:
        """
        Plot annual cost breakdown by category.
        
        Args:
            result: TCOResult object
            show: Whether to display the plot
            
        Returns:
            Matplotlib figure
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # EV annual costs
        ev_df = result.ev_results.to_dataframe()
        cost_cols = ['Purchase Cost', 'Fuel Cost', 'Maintenance', 'Insurance', 'Charger Cost']
        cost_cols = [col for col in cost_cols if col in ev_df.columns]
        
        ev_df[cost_cols].plot(kind='bar', ax=ax1, stacked=True)
        ax1.set_title(f'{result.ev_results.vehicle_name} - Annual Costs')
        ax1.set_ylabel('Cost ($)')
        ax1.set_xlabel('Year')
        ax1.legend(loc='upper left', fontsize=9)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}k'))
        
        # ICE annual costs
        ice_df = result.ice_results.to_dataframe()
        ice_df[cost_cols].plot(kind='bar', ax=ax2, stacked=True)
        ax2.set_title(f'{result.ice_results.vehicle_name} - Annual Costs')
        ax2.set_ylabel('Cost ($)')
        ax2.set_xlabel('Year')
        ax2.legend(loc='upper left', fontsize=9)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}k'))
        
        plt.tight_layout()
        if show:
            plt.show()
        
        return fig
    
    @staticmethod
    def plot_sensitivity(result: TCOResult, parameter: str = 'fuel_cost',
                        variation_range: tuple = (0.5, 1.5), show: bool = True) -> plt.Figure:
        """
        Plot sensitivity analysis for a parameter.
        
        Args:
            result: TCOResult object
            parameter: Parameter to vary ('fuel_cost', 'purchase_price', 'discount_rate')
            variation_range: Tuple of (min_multiplier, max_multiplier)
            show: Whether to display the plot
            
        Returns:
            Matplotlib figure
        """
        # This is a placeholder for sensitivity analysis
        # Would require recalculating with different parameters
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f'Sensitivity Analysis - {parameter}\n(To be implemented)',
               ha='center', va='center', fontsize=14)
        ax.axis('off')
        
        if show:
            plt.show()
        
        return fig
