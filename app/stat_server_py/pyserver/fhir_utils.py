"""
FHIR Resource Utilities Module

This module provides utility functions for fetching and processing FHIR resources
from a HAPI FHIR server. It includes functions for extracting patient details,
resource display names, and aggregating resources by type.
"""

import logging
import requests
import datetime
import io
import numpy as np
import matplotlib.pyplot as plt
from fastapi import HTTPException, Response, Query
from typing import Dict, List, Set, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

class FHIRResourceProcessor:
    def __init__(self, hapi_url: str):
        """
        Initialize the FHIR Resource Processor.
        
        Args:
            hapi_url: The base URL of the HAPI FHIR server
        """
        self.hapi_url = hapi_url.rstrip('/')
        
    async def fetch_fhir_resources(self, resource_type: str, include_patient: bool = True, count: int = 1000) -> Dict:
        """
        Fetch FHIR resources with included patient data.
        
        Args:
            resource_type: The FHIR resource type to fetch (e.g., 'Condition', 'Procedure', 'Observation')
            include_patient: Whether to include patient resources
            count: Maximum number of resources to fetch
            
        Returns:
            dict: The FHIR Bundle response
        """
        try:
            logger.info(f"Fetching {resource_type} resources from HAPI FHIR server")
            
            include_param = f"&_include={resource_type}:patient" if include_patient else ""
            url = f"{self.hapi_url}/{resource_type}?_count={count}{include_param}"
            
            logger.info(f"Making direct FHIR API call to: {url}")
            response = requests.get(url)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            error_msg = f"Error connecting to HAPI FHIR server: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def extract_patient_details(self, resource: Dict) -> Optional[str]:
        """
        Extract patient details from a FHIR Patient resource and format as a string.
        
        Args:
            resource: The FHIR Patient resource
            
        Returns:
            str: Formatted patient details string with ID, gender, and age
        """
        patient_id = resource.get('id')
        if not patient_id:
            return None
            
        # Extract gender
        gender = resource.get('gender', 'unknown')
        gender_display = gender.capitalize() if gender != 'unknown' else 'Unknown gender'
        
        # Extract birth date and calculate age
        birth_date = resource.get('birthDate', '')
        age_str = 'Unknown age'
        
        if birth_date:
            try:
                # Parse the birth date
                birth_date_obj = datetime.datetime.strptime(birth_date, '%Y-%m-%d').date()
                
                # Calculate age
                today = datetime.date.today()
                age = today.year - birth_date_obj.year
                
                # Adjust age if birthday hasn't occurred yet this year
                if (today.month, today.day) < (birth_date_obj.month, birth_date_obj.day):
                    age -= 1
                    
                age_str = f"{age} years"
            except ValueError:
                # If date format is invalid
                pass
        
        # Format the patient details as a string
        return f"ID: {patient_id}, {gender_display}, {age_str}"

    def extract_display_name(self, resource: Dict, resource_type: str) -> str:
        """
        Extract display name from a FHIR resource.
        
        Args:
            resource: The FHIR resource
            resource_type: The type of resource ('Condition', 'Procedure', 'Observation')
            
        Returns:
            str: The display name of the resource
        """
        default_name = f"Unknown {resource_type}"
        
        # For most resources, the display name is in the code.coding.display or code.text
        if 'code' in resource:
            # First try to get from coding.display
            if 'coding' in resource['code'] and resource['code']['coding']:
                for coding in resource['code']['coding']:
                    if 'display' in coding:
                        return coding['display']
            
            # If not found, try code.text
            if 'text' in resource['code']:
                return resource['code']['text']
        
        # For observations, we might want to include the value
        if resource_type == 'Observation':
            display_name = default_name
            value_summary = ""
            
            # Get the basic display name first
            if 'code' in resource:
                if 'coding' in resource['code'] and resource['code']['coding']:
                    for coding in resource['code']['coding']:
                        if 'display' in coding:
                            display_name = coding['display']
                            break
                elif 'text' in resource['code']:
                    display_name = resource['code']['text']
            
            # Then add the value if available
            if 'valueQuantity' in resource:
                value = resource['valueQuantity'].get('value')
                unit = resource['valueQuantity'].get('unit')
                if value is not None:
                    value_summary = f"{value} {unit if unit else ''}".strip()
            elif 'valueCodeableConcept' in resource:
                if 'coding' in resource['valueCodeableConcept'] and resource['valueCodeableConcept']['coding']:
                    value_summary = resource['valueCodeableConcept']['coding'][0].get('display', '')
            elif 'valueString' in resource:
                value_summary = resource['valueString']
                
            # Combine display name with value summary if available
            if value_summary:
                return f"{display_name}: {value_summary}"
            return display_name
        
        return default_name

    def extract_patient_reference(self, resource: Dict) -> Optional[str]:
        """
        Extract patient reference from a FHIR resource.
        
        Args:
            resource: The FHIR resource
            
        Returns:
            str or None: The patient ID or None if not found
        """
        if 'subject' in resource and 'reference' in resource['subject']:
            patient_ref = resource['subject']['reference']
            if patient_ref.startswith('Patient/'):
                return patient_ref[8:]
        return None

    def extract_codes(self, resource: Dict) -> Set[str]:
        """
        Extract codes from a FHIR resource.
        
        Args:
            resource: The FHIR resource
            
        Returns:
            set: Set of codes
        """
        codes = set()
        if 'code' in resource and 'coding' in resource['code'] and resource['code']['coding']:
            for coding in resource['code']['coding']:
                if 'code' in coding:
                    codes.add(coding['code'])
        return codes

    async def process_fhir_resources(self, resource_type: str, include_patients: bool = True, include_patient_details: bool = True) -> Dict:
        """
        Process FHIR resources and return a summary.
        
        Args:
            resource_type: The FHIR resource type to process (e.g., 'Condition', 'Procedure', 'Observation')
            include_patients: Whether to include patient IDs
            include_patient_details: Whether to include detailed patient information
            
        Returns:
            dict: Summary of the resources
        """
        try:
            # Fetch the resources
            bundle = await self.fetch_fhir_resources(resource_type, include_patient=include_patient_details)
            
            if not bundle or 'entry' not in bundle or not bundle['entry']:
                logger.info(f"No {resource_type.lower()}s found in the HAPI FHIR server")
                return {f"{resource_type.lower()}s": [], "total_count": 0}
            
            # Dictionary to store resources by display name
            resources_by_display = {}
            # Dictionary to store patient details by ID
            patients_by_id = {}
            
            # Process each entry in the bundle
            for entry in bundle['entry']:
                resource = entry.get('resource', {})
                entry_resource_type = resource.get('resourceType')
                
                # Process Patient resources to extract patient details
                if entry_resource_type == 'Patient':
                    try:
                        patient_id = resource.get('id')
                        patient_details = self.extract_patient_details(resource)
                        if patient_details and patient_id:
                            patients_by_id[patient_id] = patient_details
                    except Exception as e:
                        logger.warning(f"Error processing patient {resource.get('id', 'unknown')}: {str(e)}")
                
                # Process the main resource type
                elif entry_resource_type == resource_type:
                    try:
                        # Extract display name
                        display_name = self.extract_display_name(resource, resource_type)
                        
                        # Extract patient reference
                        patient_id = self.extract_patient_reference(resource)
                        
                        # Extract codes
                        codes = self.extract_codes(resource)
                        
                        # Initialize entry for this display name if not exists
                        if display_name not in resources_by_display:
                            resources_by_display[display_name] = {
                                "patient_ids": set(),
                                "count": 0,
                                "codes": set()
                            }
                        
                        # Add patient to this resource
                        if patient_id:
                            resources_by_display[display_name]["patient_ids"].add(patient_id)
                        
                        # Increment count
                        resources_by_display[display_name]["count"] += 1
                        
                        # Add codes
                        resources_by_display[display_name]["codes"].update(codes)
                    
                    except Exception as e:
                        logger.warning(f"Error processing {resource_type.lower()} {resource.get('id', 'unknown')}: {str(e)}")
            
            # Convert the resources_by_display to the final format
            resource_summary = []
            resource_name_singular = resource_type.lower()
            code_field_name = f"{resource_name_singular}_codes"
            
            for display_name, data in resources_by_display.items():
                summary_item = {
                    f"{resource_name_singular}_name": display_name,
                    "count": data["count"],
                    "patient_count": len(data["patient_ids"]),
                    code_field_name: list(data["codes"])
                }
                
                # Add patient information based on the requested detail level
                if include_patients:
                    if include_patient_details:
                        # Get patient details for each patient ID
                        patient_details = []
                        for patient_id in data["patient_ids"]:
                            if patient_id in patients_by_id:
                                # Patient details are already formatted as a string
                                patient_details.append(patients_by_id[patient_id])
                            else:
                                # For patients without details, just show the ID
                                patient_details.append(f"ID: {patient_id}, Unknown gender, Unknown age")
                        summary_item["patients"] = patient_details
                    else:
                        # Just include the patient IDs
                        summary_item["patient_ids"] = list(data["patient_ids"])
                
                resource_summary.append(summary_item)
            
            # Sort by frequency (most common first)
            resource_summary.sort(key=lambda x: x["count"], reverse=True)
            
            resource_name_plural = f"{resource_name_singular}s"
            return {
                resource_name_plural: resource_summary,
                f"total_{resource_name_plural}": sum(r["count"] for r in resource_summary),
                f"unique_{resource_name_singular}_types": len(resource_summary),
                "total_patients": len(patients_by_id) if include_patient_details else None
            }
        
        except Exception as e:
            error_msg = f"Error retrieving all {resource_type.lower()}s: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)
            
    def _get_image_response(self, plt) -> Response:
        """
        Helper function to convert matplotlib plot to FastAPI response
        
        Args:
            plt: Matplotlib pyplot instance
            
        Returns:
            Response: FastAPI response with PNG image
        """
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()  # Close the figure to free memory
        buf.seek(0)
        
        return Response(content=buf.getvalue(), media_type="image/png")
    
    def _prepare_visualization_data(self, resource_data: Dict, resource_type: str, limit: int = 20) -> Tuple[List[str], List[int]]:
        """
        Prepare data for visualization from resource summary
        
        Args:
            resource_data: Resource data from process_fhir_resources
            resource_type: Type of resource ('Condition', 'Procedure', 'Observation')
            limit: Maximum number of items to include
            
        Returns:
            Tuple[List[str], List[int]]: Names and counts for visualization
        """
        resource_name_plural = resource_type.lower() + 's'
        name_field = resource_type.lower() + '_name'
        
        if not resource_data or resource_name_plural not in resource_data or not resource_data[resource_name_plural]:
            return [], []
        
        # Sort resources by count and take the top 'limit'
        resources = sorted(resource_data[resource_name_plural], key=lambda x: x["count"], reverse=True)[:limit]
        
        # Extract names and counts
        names = []
        counts = []
        
        for resource in resources:
            # Truncate long names for better display
            name = resource[name_field]
            if len(name) > 40:
                name = name[:37] + "..."
            names.append(name)
            counts.append(resource["count"])
            
        return names, counts
        
    def _extract_age_from_patient_detail(self, patient_detail: str) -> Optional[int]:
        """
        Extract age from patient detail string
        
        Args:
            patient_detail: String containing patient details in format "ID: <id>, <Gender>, Age: <age>"
            
        Returns:
            int: Age in years, or None if not found
        """
        try:
            # Format is "ID: <id>, <Gender>, Age: <age>"
            parts = patient_detail.split(", ")
            if len(parts) >= 3:
                age_part = parts[2]  # Should be "Age: <age>"
                if "age:" in age_part.lower():
                    age_str = age_part.lower().replace("age:", "").strip()
                    if age_str.endswith("y"):  # Handle "23y" format
                        age_str = age_str[:-1]
                    if age_str.isdigit():
                        return int(age_str)
        except Exception:
            pass
        return None
    
    def _get_age_bracket(self, age: int, bracket_size: int = 5) -> str:
        """
        Get age bracket for a given age
        
        Args:
            age: Age in years
            bracket_size: Size of each age bracket in years
            
        Returns:
            str: Age bracket label (e.g., "0-4", "5-9", etc.)
        """
        if age < 0:
            return "Unknown"
        
        lower_bound = (age // bracket_size) * bracket_size
        upper_bound = lower_bound + bracket_size - 1
        return f"{lower_bound}-{upper_bound}"
    
    def _prepare_gender_visualization_data(self, resource_data: Dict, resource_type: str, limit: int = 10) -> Dict[str, Tuple[List[str], List[int]]]:
        """
        Prepare gender-specific data for visualization from resource summary
        
        Args:
            resource_data: Resource data from process_fhir_resources with patient details
            resource_type: Type of resource ('Condition', 'Procedure', 'Observation')
            limit: Maximum number of items to include per gender
            
        Returns:
            Dict[str, Tuple[List[str], List[int]]]: Gender-specific names and counts for visualization
        """
        resource_name_plural = resource_type.lower() + 's'
        name_field = resource_type.lower() + '_name'
        
        if not resource_data or resource_name_plural not in resource_data or not resource_data[resource_name_plural]:
            return {}
        
        # Create gender-specific data structures
        gender_data = {}
        resources = resource_data[resource_name_plural]
        
        # Process each resource and organize by gender
        for resource in resources:
            if "patients" not in resource:
                continue
                
            # Extract resource name
            name = resource[name_field]
            if len(name) > 40:
                name = name[:37] + "..."
                
            # Group patients by gender
            gender_counts = {}
            for patient_detail in resource["patients"]:
                # Extract gender from patient detail string
                # Format is "ID: <id>, <Gender>, <Age>"
                try:
                    parts = patient_detail.split(", ")
                    if len(parts) >= 2:
                        gender = parts[1].lower()
                        gender_counts[gender] = gender_counts.get(gender, 0) + 1
                except Exception:
                    continue
            
            # Add to gender-specific data
            for gender, count in gender_counts.items():
                if gender not in gender_data:
                    gender_data[gender] = {"names": [], "counts": []}
                
                # Check if this resource is already in the list for this gender
                if name in gender_data[gender]["names"]:
                    idx = gender_data[gender]["names"].index(name)
                    gender_data[gender]["counts"][idx] += count
                else:
                    gender_data[gender]["names"].append(name)
                    gender_data[gender]["counts"].append(count)
        
        # Sort and limit data for each gender
        result = {}
        for gender, data in gender_data.items():
            # Sort by count (descending)
            sorted_indices = sorted(range(len(data["counts"])), key=lambda i: data["counts"][i], reverse=True)
            
            # Take top 'limit' items
            names = [data["names"][i] for i in sorted_indices[:limit]]
            counts = [data["counts"][i] for i in sorted_indices[:limit]]
            
            result[gender] = (names, counts)
            
        return result
        
    def _prepare_age_bracket_visualization_data(self, resource_data: Dict, resource_type: str, limit: int = 10, bracket_size: int = 5) -> Dict[str, Tuple[List[str], List[int]]]:
        """
        Prepare age bracket-specific data for visualization from resource summary
        
        Args:
            resource_data: Resource data from process_fhir_resources with patient details
            resource_type: Type of resource ('Condition', 'Procedure', 'Observation')
            limit: Maximum number of items to include per age bracket
            bracket_size: Size of each age bracket in years
            
        Returns:
            Dict[str, Tuple[List[str], List[int]]]: Age bracket-specific names and counts for visualization
        """
        resource_name_plural = resource_type.lower() + 's'
        name_field = resource_type.lower() + '_name'
        
        if not resource_data or resource_name_plural not in resource_data or not resource_data[resource_name_plural]:
            return {}
        
        # Create age bracket-specific data structures
        age_bracket_data = {}
        resources = resource_data[resource_name_plural]
        
        # Process each resource and organize by age bracket
        for resource in resources:
            if "patients" not in resource:
                continue
                
            # Extract resource name
            name = resource[name_field]
            if len(name) > 40:
                name = name[:37] + "..."
                
            # Group patients by age bracket
            age_bracket_counts = {}
            for patient_detail in resource["patients"]:
                # Extract age from patient detail string
                age = self._extract_age_from_patient_detail(patient_detail)
                if age is not None:
                    age_bracket = self._get_age_bracket(age, bracket_size)
                    age_bracket_counts[age_bracket] = age_bracket_counts.get(age_bracket, 0) + 1
            
            # Add to age bracket-specific data
            for age_bracket, count in age_bracket_counts.items():
                if age_bracket not in age_bracket_data:
                    age_bracket_data[age_bracket] = {"names": [], "counts": []}
                
                # Check if this resource is already in the list for this age bracket
                if name in age_bracket_data[age_bracket]["names"]:
                    idx = age_bracket_data[age_bracket]["names"].index(name)
                    age_bracket_data[age_bracket]["counts"][idx] += count
                else:
                    age_bracket_data[age_bracket]["names"].append(name)
                    age_bracket_data[age_bracket]["counts"].append(count)
        
        # Sort and limit data for each age bracket
        result = {}
        
        # Sort age brackets naturally
        sorted_brackets = sorted(age_bracket_data.keys(), 
                               key=lambda x: int(x.split('-')[0]) if x != "Unknown" else float('inf'))
        
        for age_bracket in sorted_brackets:
            data = age_bracket_data[age_bracket]
            # Sort by count (descending)
            sorted_indices = sorted(range(len(data["counts"])), key=lambda i: data["counts"][i], reverse=True)
            
            # Take top 'limit' items
            names = [data["names"][i] for i in sorted_indices[:limit]]
            counts = [data["counts"][i] for i in sorted_indices[:limit]]
            
            result[age_bracket] = (names, counts)
            
        return result
    
    async def visualize_resource(self, resource_type: str, limit: int = 20) -> Response:
        """
        Generate a bar chart visualization of the most common resource types.
        
        Args:
            resource_type: Type of resource to visualize ('Condition', 'Procedure', 'Observation')
            limit: Maximum number of items to include
            
        Returns:
            Response: PNG image of the visualization
        """
        try:
            logger.info(f"Generating visualization of {resource_type.lower()}s")
            
            # Get resource data without patient details
            resource_data = await self.process_fhir_resources(resource_type, include_patients=False)
            
            # Prepare data for visualization
            names, counts = self._prepare_visualization_data(resource_data, resource_type, limit)
            
            if not names or not counts:
                # Return a simple image saying no data
                plt.figure(figsize=(10, 6))
                plt.text(0.5, 0.5, f"No {resource_type.lower()} data available", 
                         horizontalalignment='center', verticalalignment='center', fontsize=14)
                plt.axis('off')
                return self._get_image_response(plt)
            
            # Create the visualization
            plt.figure(figsize=(12, max(6, len(names) * 0.3)))  # Adjust height based on number of items
            
            # Create horizontal bar chart
            y_pos = np.arange(len(names))
            plt.barh(y_pos, counts, align='center', alpha=0.7, color='skyblue')
            plt.yticks(y_pos, names)
            plt.xlabel('Number of Occurrences')
            plt.title(f'Most Common {resource_type} Types')
            plt.tight_layout()
            
            # Add count labels to the bars
            for i, v in enumerate(counts):
                plt.text(v + 0.1, i, str(v), color='black', va='center')
            
            # Return the image as a response
            return self._get_image_response(plt)
            
        except Exception as e:
            error_msg = f"Error generating {resource_type.lower()} visualization: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)
            
    async def visualize_resource_by_gender(self, resource_type: str, limit: int = 10) -> Response:
        """
        Generate a visualization of resources broken down by gender
        
        Args:
            resource_type: Type of resource ('Condition', 'Procedure', 'Observation')
            limit: Maximum number of items to include per gender
            
        Returns:
            FastAPI Response with PNG image
        """
        try:
            # Process resources with patient details
            resource_data = await self.process_fhir_resources(
                resource_type, 
                include_patients=True,
                include_patient_details=True
            )
            
            # Prepare data for visualization by gender
            gender_data = self._prepare_gender_visualization_data(resource_data, resource_type, limit)
            
            if not gender_data:
                return Response(content="No data available for visualization", media_type="text/plain")
            
            # Set up the figure based on number of genders
            num_genders = len(gender_data)
            fig_height = max(4, 2 + num_genders * 0.5)  # Base height + additional height per gender
            
            # Create figure with subplots - one row per gender
            fig, axes = plt.subplots(num_genders, 1, figsize=(10, fig_height * num_genders), squeeze=False)
            
            # Color mapping for genders
            color_map = {
                "male": "lightblue",
                "female": "lightpink",
                # Default for any other gender
                "other": "lightgreen"
            }
            
            # Plot data for each gender
            for i, (gender, (names, counts)) in enumerate(gender_data.items()):
                ax = axes[i, 0]
                
                # Get color for this gender
                color = color_map.get(gender.lower(), color_map["other"])
                
                # Create positions for bars
                y_pos = np.arange(len(names))
                
                # Create horizontal bar chart
                ax.barh(y_pos, counts, align='center', alpha=0.7, color=color)
                ax.set_yticks(y_pos)
                ax.set_yticklabels(names)
                ax.invert_yaxis()  # Labels read top-to-bottom
                ax.set_xlabel('Number of Occurrences')
                ax.set_title(f'Most Common {resource_type} Types - {gender.capitalize()}')
                
                # Add count labels to bars
                for j, v in enumerate(counts):
                    ax.text(v + 0.1, j, str(v), color='black', va='center')
            
            plt.tight_layout(pad=3.0)
            
            # Convert plot to PNG image
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            
            return Response(content=buf.getvalue(), media_type="image/png")
            
        except Exception as e:
            logging.error(f"Error generating visualization by gender for {resource_type}: {str(e)}")
            return Response(
                content=f"Error generating visualization: {str(e)}", 
                media_type="text/plain"
            )
            
    async def visualize_resource_by_age_bracket(self, resource_type: str, limit: int = 10, bracket_size: int = 5) -> Response:
        """
        Generate a visualization of resources broken down by age brackets
        
        Args:
            resource_type: Type of resource ('Condition', 'Procedure', 'Observation')
            limit: Maximum number of items to include per age bracket
            bracket_size: Size of each age bracket in years
            
        Returns:
            FastAPI Response with PNG image
        """
        try:
            # Process resources with patient details
            resource_data = await self.process_fhir_resources(
                resource_type, 
                include_patients=True,
                include_patient_details=True
            )
            
            # Prepare data for visualization by age bracket
            age_bracket_data = self._prepare_age_bracket_visualization_data(
                resource_data, resource_type, limit, bracket_size
            )
            
            if not age_bracket_data:
                return Response(content="No age data available for visualization", media_type="text/plain")
            
            # Set up the figure based on number of age brackets
            num_brackets = len(age_bracket_data)
            fig_height = max(4, 2 + num_brackets * 0.5)  # Base height + additional height per bracket
            
            # Create figure with subplots - one row per age bracket
            fig, axes = plt.subplots(num_brackets, 1, figsize=(10, fig_height * num_brackets), squeeze=False)
            
            # Generate a color gradient for age brackets
            colors = plt.cm.viridis(np.linspace(0, 0.8, num_brackets))
            
            # Plot data for each age bracket
            for i, (age_bracket, (names, counts)) in enumerate(age_bracket_data.items()):
                ax = axes[i, 0]
                
                # Create positions for bars
                y_pos = np.arange(len(names))
                
                # Create horizontal bar chart
                ax.barh(y_pos, counts, align='center', alpha=0.7, color=colors[i])
                ax.set_yticks(y_pos)
                ax.set_yticklabels(names)
                ax.invert_yaxis()  # Labels read top-to-bottom
                ax.set_xlabel('Number of Occurrences')
                ax.set_title(f'Most Common {resource_type} Types - Age {age_bracket} years')
                
                # Add count labels to bars
                for j, v in enumerate(counts):
                    ax.text(v + 0.1, j, str(v), color='black', va='center')
            
            plt.tight_layout(pad=3.0)
            
            # Convert plot to PNG image
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            
            return Response(content=buf.getvalue(), media_type="image/png")
            
        except Exception as e:
            logger.error(f"Error generating visualization by age bracket for {resource_type}: {str(e)}", exc_info=True)
            return Response(
                content=f"Error generating visualization: {str(e)}", 
                media_type="text/plain"
            )
