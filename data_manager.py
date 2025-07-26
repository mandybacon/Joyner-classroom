import pandas as pd
import os
from datetime import datetime
import pytz
import csv

class DataManager:
    """Handles data persistence and management for behavior tracking"""
    
    def __init__(self, data_file='behavior_data.csv'):
        self.data_file = data_file
        self.behavior_data = None
        
    def load_or_create_behavior_data(self, student_names):
        """Load existing behavior data or create new DataFrame with student names"""
        try:
            if os.path.exists(self.data_file):
                self.behavior_data = pd.read_csv(self.data_file)
                # Ensure all students are in the data
                self._ensure_all_students_exist(student_names)
            else:
                # Create new DataFrame
                self.behavior_data = pd.DataFrame({'student': [], 'date': [], 'color': []})
                
        except Exception as e:
            print(f"Error loading behavior data: {e}")
            # Create new DataFrame as fallback
            self.behavior_data = pd.DataFrame({'student': [], 'date': [], 'color': []})
    
    def _ensure_all_students_exist(self, student_names):
        """Ensure all students from the roster exist in our data tracking"""
        if self.behavior_data is None:
            return
            
        existing_students = set(self.behavior_data['student'].unique())
        new_students = set(student_names) - existing_students
        
        # We don't need to add rows for new students immediately
        # They'll be added when behavior is first recorded
        
    def add_behavior_entry(self, student_name, color, date=None):
        """Add a new behavior entry for a student"""
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Check if entry already exists for this student and date
            if self.behavior_data is not None:
                existing_entry = self.behavior_data[
                    (self.behavior_data['student'] == student_name) & 
                    (self.behavior_data['date'] == date)
                ]
                
                if not existing_entry.empty:
                    # Update existing entry
                    self.behavior_data.loc[
                        (self.behavior_data['student'] == student_name) & 
                        (self.behavior_data['date'] == date), 
                        'color'
                    ] = color
                else:
                    # Add new entry
                    new_entry = pd.DataFrame({
                        'student': [student_name],
                        'date': [date],
                        'color': [color]
                    })
                    self.behavior_data = pd.concat([self.behavior_data, new_entry], ignore_index=True)
            else:
                # Create new DataFrame with first entry
                self.behavior_data = pd.DataFrame({
                    'student': [student_name],
                    'date': [date],
                    'color': [color]
                })
            
            # Save to file
            return self._save_behavior_data()
            
        except Exception as e:
            print(f"Error adding behavior entry: {e}")
            return False
    
    def get_student_behavior_data(self, student_name):
        """Get all behavior data for a specific student"""
        if self.behavior_data is None or self.behavior_data.empty:
            return pd.DataFrame()
        
        student_data = self.behavior_data[self.behavior_data['student'] == student_name].copy()
        
        if not student_data.empty:
            # Convert date column to datetime for proper sorting
            student_data = student_data.copy()
            student_data['date'] = pd.to_datetime(student_data['date'])
            student_data = student_data.sort_values(by='date')
        
        return student_data
    
    def get_all_behavior_data(self):
        """Get all behavior data"""
        return self.behavior_data if self.behavior_data is not None else pd.DataFrame()
    
    def _save_behavior_data(self):
        """Save behavior data to CSV file"""
        try:
            if self.behavior_data is not None:
                self.behavior_data.to_csv(self.data_file, index=False)
                return True
            return False
        except Exception as e:
            print(f"Error saving behavior data: {e}")
            return False
    
    def export_behavior_data(self, filename=None):
        """Export behavior data to a specified file"""
        if filename is None:
            chicago_tz = pytz.timezone('America/Chicago')
            timestamp = datetime.now(chicago_tz).strftime("%Y%m%d_%H%M%S")
            filename = f"behavior_export_{timestamp}.csv"
        
        try:
            if self.behavior_data is not None and not self.behavior_data.empty:
                self.behavior_data.to_csv(filename, index=False)
                return filename
            return None
        except Exception as e:
            print(f"Error exporting behavior data: {e}")
            return None
    
    def get_student_summary(self, student_name):
        """Get summary statistics for a student"""
        student_data = self.get_student_behavior_data(student_name)
        
        if student_data.empty:
            return None
        
        color_counts = pd.Series(student_data['color']).value_counts()
        total_entries = len(student_data)
        
        summary = {
            'total_entries': total_entries,
            'color_distribution': color_counts.to_dict(),
            'most_recent_date': student_data['date'].max(),
            'first_entry_date': student_data['date'].min()
        }
        
        return summary
    
    def get_class_summary(self):
        """Get summary statistics for the entire class"""
        if self.behavior_data is None or self.behavior_data.empty:
            return None
        
        total_students = self.behavior_data['student'].nunique()
        total_entries = len(self.behavior_data)
        color_distribution = self.behavior_data['color'].value_counts()
        
        summary = {
            'total_students': total_students,
            'total_entries': total_entries,
            'color_distribution': color_distribution.to_dict(),
            'students_with_data': self.behavior_data['student'].unique().tolist()
        }
        
        return summary
    
    def clear_student_data(self, student_name):
        """Clear all behavior data for a specific student"""
        try:
            if self.behavior_data is not None and not self.behavior_data.empty:
                # Remove all entries for the specified student
                self.behavior_data = self.behavior_data[self.behavior_data['student'] != student_name]
                return self._save_behavior_data()
            return True
        except Exception as e:
            print(f"Error clearing student data: {e}")
            return False
    
    def clear_all_data(self):
        """Clear all behavior data for all students"""
        try:
            # Create empty DataFrame with proper structure
            self.behavior_data = pd.DataFrame(columns=['student', 'date', 'color'])
            return self._save_behavior_data()
        except Exception as e:
            print(f"Error clearing all data: {e}")
            return False
