import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
import yaml
import os
import logging
from datetime import datetime, timedelta
# from sklearn.model_selection import train_test_split # Needed for split_time_to_event_data
# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def load_configuration(config_filepath: str) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    try:
        with open(config_filepath, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_filepath}")
        raise RuntimeError(f"Configuration file not found: {config_filepath}")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration YAML: {e}")
        raise RuntimeError(f"Error parsing configuration YAML: {e}")
def get_aou_cdr_path() -> str:
    """Returns the base path for the All of Us Controlled Tier Dataset."""
    if "WORKSPACE_CDR" not in os.environ:
        raise EnvironmentError("WORKSPACE_CDR environment variable not set. "
                               "This is required in the All of Us Workbench.")
    return os.environ["WORKSPACE_CDR"]
def _build_ancestor_descendant_sql(cdr_path: str, ancestor_concept_ids: List[int]) -> str:
    """
    Builds a SQL subquery to select all descendant concept IDs for given ancestor concept IDs
    using cb_criteria_ancestor and cb_criteria.
    """
    if not ancestor_concept_ids:
        return "SELECT concept_id FROM `dummy_table` WHERE FALSE"

    ancestor_ids_str = ','.join(map(str, ancestor_concept_ids))

    sql = f"""
    SELECT
        DISTINCT ca.descendant_id
    FROM
        `{cdr_path}.cb_criteria_ancestor` ca
    JOIN
        (
            SELECT
                DISTINCT c.concept_id
            FROM
                `{cdr_path}.cb_criteria` c
            JOIN
                (
                    SELECT
                        cast(cr.id as string) as id
                    FROM
                        `{cdr_path}.cb_criteria` cr
                    WHERE
                        concept_id IN ({ancestor_ids_str})
                        AND full_text LIKE '%_rank1]%'
                ) a
                ON (
                    c.path LIKE CONCAT('%.', a.id, '.%')
                    OR c.path LIKE CONCAT('%.', a.id)
                    OR c.path LIKE CONCAT(a.id, '.%')
                    OR c.path = a.id
                )
            WHERE
                is_standard = 1
                AND is_selectable = 1
        ) b
        ON (ca.ancestor_id = b.concept_id)
    """
    return sql
def _get_concept_filter_sql(domain_table_alias: str, concept_id_col_name: str, concepts_config: Dict[str, Any], cdr_path: str) -> str:
    """
    Generates SQL filter condition for including/excluding concepts, supporting ancestor mapping.
    """
    include_concepts = concepts_config.get('concepts_include', [])
    exclude_concepts = concepts_config.get('concepts_exclude', [])
    map_to_descendants = concepts_config.get('map_to_descendants', False)

    include_conditions = []
    exclude_conditions = []

    if include_concepts:
        if map_to_descendants:
            include_sql = _build_ancestor_descendant_sql(cdr_path, include_concepts)
            include_conditions.append(f"{domain_table_alias}.{concept_id_col_name} IN ({include_sql})")
        else:
            include_conditions.append(f"{domain_table_alias}.{concept_id_col_name} IN ({','.join(map(str, include_concepts))})")

    if exclude_concepts:
        if map_to_descendants:
            exclude_sql = _build_ancestor_descendant_sql(cdr_path, exclude_concepts)
            exclude_conditions.append(f"{domain_table_alias}.{concept_id_col_name} NOT IN ({exclude_sql})")
        else:
            exclude_conditions.append(f"{domain_table_alias}.{concept_id_col_name} NOT IN ({','.join(map(str, exclude_concepts))})")
    
    final_conditions = []
    if include_conditions:
        final_conditions.append(f"({' OR '.join(include_conditions)})")
    if exclude_conditions:
        final_conditions.append(f"({' AND '.join(exclude_conditions)})")

    return " AND ".join(final_conditions) if final_conditions else ""
def build_domain_events_query(domain_name: str, concept_config: Dict[str, Any], cdr_path: str,
                              feature_metadata_name: str, feature_metadata_type: str) -> str: # <--- CORRECTED SIGNATURE
    """
    Builds a SQL query to extract all relevant events for a given domain and concept configuration.
    Returns basic columns needed for time-based filtering later.
    """
    domain_table_name = domain_name
    domain_table = f"`{cdr_path}.{domain_table_name}`"
    
    concept_id_col_name = ""
    date_col_name = ""
    value_col_expression = "NULL" 
    value_type_inferred_from_domain = ""
    additional_select_cols = [] 

    if domain_name == 'condition_occurrence':
        concept_id_col_name = 'condition_concept_id'
        date_col_name = 'condition_start_datetime'
        additional_select_cols.append("t.condition_end_datetime")
        value_col_expression = "1"
        value_type_inferred_from_domain = "binary"
    elif domain_name == 'condition_era':
        concept_id_col_name = 'condition_concept_id' 
        date_col_name = 'condition_era_start_datetime'
        additional_select_cols.append("t.condition_era_end_datetime")
        value_col_expression = "1" 
        value_type_inferred_from_domain = "binary"
    elif domain_name == 'observation':
        concept_id_col_name = 'observation_concept_id'
        date_col_name = 'observation_datetime'
        value_col_expression = 't.value_as_number'
        value_type_inferred_from_domain = 'continuous'
        if concept_config.get('type') == 'categorical' or concept_config.get('type') == 'binary':
            value_col_expression = 't.value_as_concept_id'
            value_type_inferred_from_domain = concept_config.get('type')
    elif domain_name == 'measurement':
        concept_id_col_name = 'measurement_concept_id'
        date_col_name = 'measurement_datetime'
        value_col_expression = 't.value_as_number'
        value_type_inferred_from_domain = 'continuous'
    elif domain_name == 'drug_exposure':
        concept_id_col_name = 'drug_concept_id'
        date_col_name = 'drug_exposure_start_datetime'
        additional_select_cols.append("t.drug_exposure_end_datetime")
        value_col_expression = "1"
        value_type_inferred_from_domain = "binary"
    elif domain_name == 'procedure_occurrence':
        concept_id_col_name = 'procedure_concept_id'
        date_col_name = 'procedure_datetime'
        value_col_expression = "1"
        value_type_inferred_from_domain = "binary"
    else:
        logging.warning(f"Domain '{domain_name}' not explicitly supported for event extraction. Returning empty query.")
        return "" 


    # Build WHERE clauses
    where_conditions = []
    concept_filter_sql = _get_concept_filter_sql("t", concept_id_col_name, concept_config, cdr_path)
    if concept_filter_sql:
        where_conditions.append(concept_filter_sql)
    
    where_conditions.append(f"t.{date_col_name} IS NOT NULL")
    
    if domain_name == 'measurement' and value_col_expression == 't.value_as_number':
        where_conditions.append("t.value_as_number IS NOT NULL")

    final_where_clause = ""
    if where_conditions:
        final_where_clause = f"WHERE {' AND '.join(where_conditions)}"

    # Build SELECT columns
    select_cols = [
        "t.person_id",
        f"t.{concept_id_col_name} AS concept_id",
        f"t.{date_col_name} AS event_datetime",
        f"{value_col_expression} AS value"
    ]
    if additional_select_cols:
        select_cols.extend([f"{col} AS {col.split('.')[-1]}" for col in additional_select_cols])
    
    select_cols.append(f"'{feature_metadata_name}' AS feature_name")
    select_cols.append(f"'{domain_name}' AS domain_name") # This is the domain the data came from
    select_cols.append(f"'{value_type_inferred_from_domain}' AS value_type") # This is the inferred type from domain logic


    sql = f"""
    SELECT
        {', '.join(select_cols)}
    FROM
        {domain_table} t
    {final_where_clause}
    """
    return sql
def get_observation_periods_query(cdr_path: str) -> str:
    return f"""
    SELECT
        person_id,
        observation_period_start_date,
        observation_period_end_date
    FROM
        `{cdr_path}.observation_period`
    WHERE
        observation_period_start_date IS NOT NULL AND observation_period_end_date IS NOT NULL
        AND DATE_DIFF(observation_period_end_date, observation_period_start_date, DAY) >= 0
    """
def get_all_outcome_events_query(outcome_config: Dict[str, Any], cdr_path: str) -> str:
    outcome_domain = outcome_config['domain']
    outcome_concept_id_col_name = 'condition_concept_id'
    outcome_date_col_name = 'condition_start_datetime'

    concept_filter_conditions = _get_concept_filter_sql("t", outcome_concept_id_col_name, outcome_config, cdr_path)
    
    where_clauses = [f"t.{outcome_date_col_name} IS NOT NULL"]
    if concept_filter_conditions:
        where_clauses.append(concept_filter_conditions)

    final_where_clause = ""
    if where_clauses:
        final_where_clause = f"WHERE {' AND '.join(where_clauses)}"

    return f"""
    SELECT
        t.person_id,
        t.{outcome_date_col_name} AS outcome_datetime
    FROM
        `{cdr_path}.{outcome_domain}` t
    {final_where_clause}
    """
def load_data_from_bigquery(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Loads data from Google BigQuery based on the provided configuration.
    Implements cohort construction, random time_0 selection, and time-to-event outcome derivation.
    """
    client = bigquery.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    cdr_path = get_aou_cdr_path()

    logger.info("Step 1: Fetching base person demographic data.")
    base_person_query = build_person_base_query(config)
    person_df = client.query(base_person_query).to_dataframe()
    logger.info(f"Base person data loaded. Shape: {person_df.shape}")

    if person_df.empty:
        logger.warning("No persons found matching base cohort criteria. Returning empty DataFrame.")
        return pd.DataFrame()

    logger.info("Step 2: Fetching observation periods for all persons.")
    obs_period_query = get_observation_periods_query(cdr_path)
    obs_period_df = client.query(obs_period_query).to_dataframe()
    logger.info(f"Observation periods loaded. Shape: {obs_period_df.shape}")
    # CRITICAL FIX 1: Ensure observation period dates are timezone-naive immediately after load
    obs_period_df['observation_period_start_date'] = pd.to_datetime(obs_period_df['observation_period_start_date']).dt.tz_localize(None)
    obs_period_df['observation_period_end_date'] = pd.to_datetime(obs_period_df['observation_period_end_date']).dt.tz_localize(None)


    logger.info(f"Step 3: Fetching all outcome events (COPD) for potential filtering.")
    outcome_config = config.get('outcome')
    if not outcome_config or 'domain' not in outcome_config:
        raise ValueError("Outcome configuration missing or incomplete in YAML.")
    
    all_outcome_events_query = get_all_outcome_events_query(outcome_config, cdr_path)
    all_outcome_events_df = client.query(all_outcome_events_query).to_dataframe()
    logger.info(f"All outcome events loaded. Shape: {all_outcome_events_df.shape}")
    # CRITICAL FIX 2: Ensure outcome datetime is timezone-naive immediately after load
    all_outcome_events_df['outcome_datetime'] = pd.to_datetime(all_outcome_events_df['outcome_datetime']).dt.tz_localize(None)


    # --- Step 4: Determine a single random time_0 for each person ---
    cohort_params = config.get('cohort_parameters', {})
    MIN_LOOKBACK_DAYS = cohort_params.get('min_lookback_days', 365)
    MIN_FOLLOWUP_DAYS = cohort_params.get('min_followup_days', 365 * 5)
    
    logger.info("Step 4: Determining random time_0 for each person...")
    person_obs_outcome = pd.merge(obs_period_df, all_outcome_events_df, on='person_id', how='left')

    time_0_candidates = []
    # Use timezone-naive datetime.datetime for 'today' for consistent comparisons
    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Filter person_obs_outcome to only include rows from person_df for efficiency
    person_obs_outcome = person_obs_outcome[person_obs_outcome['person_id'].isin(person_df['person_id'])].copy()

    for person_id, group in person_obs_outcome.groupby('person_id'):
        # Get all observation periods for this person (already tz-naive from FIX 1)
        person_periods = obs_period_df[obs_period_df['person_id'] == person_id].copy()
        
        # Get all outcome dates for this person (already tz-naive from FIX 2)
        person_outcome_dates = all_outcome_events_df[all_outcome_events_df['person_id'] == person_id]['outcome_datetime'].dropna().copy().sort_values()
        first_outcome_date = person_outcome_dates.iloc[0] if not person_outcome_dates.empty else None

        valid_time_0_ranges = []
        for _, period_row in person_periods.iterrows():
            obs_start = period_row['observation_period_start_date']
            obs_end = period_row['observation_period_end_date']

            earliest_time_0_candidate = obs_start + timedelta(days=MIN_LOOKBACK_DAYS)
            latest_time_0_candidate = min(obs_end - timedelta(days=MIN_FOLLOWUP_DAYS), today_dt) # Use today_dt here

            if earliest_time_0_candidate > latest_time_0_candidate:
                continue # Period is too short

            # If there's an outcome, time_0 must be *before* the outcome date
            if first_outcome_date is not None:
                latest_time_0_candidate = min(latest_time_0_candidate, first_outcome_date - timedelta(days=1))

            if earliest_time_0_candidate <= latest_time_0_candidate:
                valid_time_0_ranges.append((earliest_time_0_candidate, latest_time_0_candidate))
        
        if valid_time_0_ranges:
            combined_duration_days = 0
            for start, end in valid_time_0_ranges:
                combined_duration_days += (end - start).days + 1

            if combined_duration_days > 0:
                random_day_offset_overall = np.random.randint(0, combined_duration_days)
                
                selected_time_0 = None
                current_day_count = 0
                for start, end in valid_time_0_ranges:
                    range_days = (end - start).days + 1
                    if random_day_offset_overall < current_day_count + range_days:
                        selected_time_0 = start + timedelta(days=random_day_offset_overall - current_day_count)
                        break
                    current_day_count += range_days
                
                if selected_time_0:
                    time_0_candidates.append({
                        'person_id': person_id,
                        'time_0': selected_time_0, # This is now a datetime.datetime object
                        'observation_period_start_date': obs_start,
                        'observation_period_end_date': obs_end,
                        'actual_outcome_datetime': first_outcome_date
                    })
    
    time_0_df = pd.DataFrame(time_0_candidates)
    
    if not time_0_df.empty:
        # These columns are already datetime.datetime objects from above, just ensure
        # they are recognized by Pandas as such and are timezone-naive
        time_0_df['time_0'] = pd.to_datetime(time_0_df['time_0']).dt.tz_localize(None)
        time_0_df['observation_period_start_date'] = pd.to_datetime(time_0_df['observation_period_start_date']).dt.tz_localize(None)
        time_0_df['observation_period_end_date'] = pd.to_datetime(time_0_df['observation_period_end_date']).dt.tz_localize(None)
        time_0_df['actual_outcome_datetime'] = pd.to_datetime(time_0_df['actual_outcome_datetime']).dt.tz_localize(None)

        time_0_df = time_0_df.groupby('person_id').sample(n=1, random_state=42, replace=True).reset_index(drop=True)
    else:
        logging.warning("No persons with valid time_0 found after filtering. Returning empty DataFrame.")
        return pd.DataFrame()
        
    logging.info(f"Determined time_0 for {time_0_df.shape[0]} unique persons.")

    person_df = pd.merge(person_df, time_0_df[['person_id', 'time_0', 'observation_period_start_date', 'observation_period_end_date', 'actual_outcome_datetime']], on='person_id', how='inner')
    
    if person_df.empty:
        logging.warning("No persons with valid time_0 found after merging. Returning empty DataFrame.")
        return pd.DataFrame()

    # --- Step 5: Derive Outcome (time_to_event_days, event_observed) ---
    logging.info("Step 5: Deriving time_to_event_days and event_observed...")
    # These should already be consistent from Step 4 / initial loads, but tz_localize(None) just in case
    # Removed the format argument as it's not always consistent with BigQuery's output string format.
    # Pandas should generally infer it correctly.
    person_df['time_0_dt'] = pd.to_datetime(person_df['time_0']).dt.tz_localize(None)
    person_df['obs_end_dt'] = pd.to_datetime(person_df['observation_period_end_date']).dt.tz_localize(None)
    person_df['actual_outcome_dt'] = pd.to_datetime(person_df['actual_outcome_datetime']).dt.tz_localize(None)


    person_df['event_observed'] = person_df['actual_outcome_dt'].notna().astype(int)
    
    time_to_event_raw = np.where(
        person_df['event_observed'] == 1,
        (person_df['actual_outcome_dt'] - person_df['time_0_dt']).dt.days,
        (person_df['obs_end_dt'] - person_df['time_0_dt']).dt.days
    )
    person_df['time_to_event_days'] = np.maximum(time_to_event_raw, 1).astype(float)
    
    logging.info("Time-to-event and event_observed derived.")
    logging.info(f"Derived outcomes: min_time={person_df['time_to_event_days'].min()}, max_time={person_df['time_to_event_days'].max()}, events={person_df['event_observed'].sum()}")

    # --- Step 6: Fetch and Join Features based on time_0 and lookbacks (OPTIMIZED) ---
    logging.info("Step 6: Fetching and joining features based on time_0 and lookback windows...")
    final_df = person_df.copy() # Start with the person data and derived outcomes

    features_to_extract = config.get('co_indicators', []) + config.get('features', [])
    
    # List of feature names that are NOT extracted via build_domain_events_query loop
    # because they are either in the base person query, derived in Python, or outcome-related.
    excluded_from_feature_extraction_loop = [
        'ethnicity', 'sex_at_birth', 'age_at_time_0', 'gender', 'race', 'person_id', 
        'date_of_birth', 'current_age', 'birth_datetime', 'year_of_birth',
        'condition_duration', 'condition_start_datetimes', 'condition_end_datetimes'
    ]

    for feature_config in features_to_extract:
        feature_name = feature_config['name']
        
        # Determine the type of feature from config, defaulting to 'binary' for co_indicators
        feature_type_from_config = feature_config.get('type')
        if feature_type_from_config is None and feature_name in [ind['name'] for ind in config.get('co_indicators', [])]:
            feature_type_from_config = 'binary'
        elif feature_type_from_config is None: # For any other feature without a type, default to binary
             feature_type_from_config = 'binary'

        # Skip features if they are explicitly excluded or person-level (handled in base query)
        if feature_name in excluded_from_feature_extraction_loop:
            logging.info(f"Skipping feature '{feature_name}': Already in base person data or derived, or excluded from extraction loop.")
            continue
        
        all_source_events_df_combined = pd.DataFrame()
        
        if 'sources' in feature_config: # This is a consolidated feature (e.g., smoking_status, alcohol_use)
            for source_config_item in feature_config['sources']: # Iterate through each source definition
                source_domain = source_config_item['domain'] # Get domain from the source item
                logging.info(f"Extracting source for consolidated feature '{feature_name}' from domain: {source_domain}")
                
                raw_events_query = build_domain_events_query(source_domain, source_config_item, cdr_path,
                                                             feature_metadata_name=feature_name,
                                                             feature_metadata_type=feature_type_from_config)
                if not raw_events_query:
                    logging.warning(f"Skipping source {source_domain} for consolidated feature {feature_name}: No valid query built.")
                    continue
                
                try:
                    source_events_df = client.query(raw_events_query).to_dataframe()
                    if not source_events_df.empty:
                        all_source_events_df_combined = pd.concat([all_source_events_df_combined, source_events_df], ignore_index=True)
                except Exception as e:
                    logging.error(f"Error querying source {source_domain} for consolidated feature {feature_name}: {e}", exc_info=True)
                    continue 
            
            feature_events_df = all_source_events_df_combined
            logging.info(f"Combined raw events for consolidated feature {feature_name}. Shape: {feature_events_df.shape}")

        else: # Logic for single-domain features (e.g., obesity, diabetes, bmi, cardiovascular_disease)
            feature_domain_for_query = feature_config.get('primary_domain') or feature_config.get('domain')
            
            if not feature_domain_for_query:
                logging.warning(f"Feature '{feature_name}' has no valid domain (primary_domain or domain) for extraction. Skipping.")
                final_df[feature_name] = np.nan
                continue
            
            logging.info(f"Extracting single-domain feature: {feature_name} from domain: {feature_domain_for_query}")
            
            raw_events_query = build_domain_events_query(feature_domain_for_query, feature_config, cdr_path,
                                                         feature_metadata_name=feature_name,
                                                         feature_metadata_type=feature_type_from_config)
            if not raw_events_query:
                logging.warning(f"Skipping feature {feature_name}: No valid query built for domain {feature_domain_for_query}.")
                feature_events_df = pd.DataFrame() 
            else:
                try:
                    feature_events_df = client.query(raw_events_query).to_dataframe()
                    logging.info(f"Raw events for {feature_name} loaded. Shape: {feature_events_df.shape}")
                except Exception as e:
                    logging.error(f"Error querying feature {feature_name} from domain {feature_domain_for_query}: {e}", exc_info=True)
                    feature_events_df = pd.DataFrame() 


        # --- NEW ROBUST CHECK for feature_events_df before processing ---
        # Define columns that MUST be present for processing (derived from build_domain_events_query's SELECT)
        required_cols_for_processing = ['person_id', 'concept_id', 'event_datetime', 'value'] 
        
        # Check if DataFrame is empty OR if it's missing any of the critically required columns
        if feature_events_df.empty or not all(col in feature_events_df.columns for col in required_cols_for_processing):
            logging.warning(f"No events found for feature {feature_name} or feature events DataFrame is missing expected columns ({required_cols_for_processing}). Defaulting to NaN for this feature. Current columns in events DF: {feature_events_df.columns.tolist()}")
            final_df[feature_name] = np.nan
            continue
        # --- END NEW ROBUST CHECK ---


        # Convert event_datetime and other dates to datetime objects and make timezone-naive
        feature_events_df['event_datetime'] = pd.to_datetime(feature_events_df['event_datetime']).dt.tz_localize(None)
        
        for col in ['condition_end_datetime', 'condition_era_end_datetime', 'drug_exposure_end_datetime', 'procedure_end_datetime']:
            if col in feature_events_df.columns:
                feature_events_df[col] = pd.to_datetime(feature_events_df[col], errors='coerce').dt.tz_localize(None)


        # --- OPTIMIZED APPLY LOOKBACK AND CONSOLIDATE LOGIC ---
        # Prepare data for vectorized operations
        person_time_data = final_df[['person_id', 'time_0_dt', 'observation_period_start_date', 'observation_period_end_date']].copy()
        events_with_time_data = pd.merge(feature_events_df, person_time_data, on='person_id', how='inner')

        if events_with_time_data.empty:
            logging.warning(f"No events for feature {feature_name} within valid time_0 range after merge. Defaulting to NaN.")
            feature_df_per_person_result = pd.DataFrame({'person_id': final_df['person_id'].unique(), feature_name: np.nan})
            final_df = pd.merge(final_df, feature_df_per_person_result, on='person_id', how='left')
            continue


        lookback_strategy = feature_config.get('lookback_strategy', 'recent_fixed')
        lookback_window_days = feature_config.get('lookback_window_days', 365)
        consolidation_method = feature_config.get('consolidation_method', 'most_recent')
        feature_type_from_config = feature_config.get('type') # Re-get as feature_type_from_config might have been derived for co_indicators.

        # Efficiently filter relevant events using vectorized operations
        relevant_events_filtered = pd.DataFrame()
        if lookback_strategy == 'chronic_ongoing':
            # Filter based on start before time_0
            relevant_events_filtered = events_with_time_data[events_with_time_data['event_datetime'] <= events_with_time_data['time_0_dt']].copy()
            # Apply end_datetime logic if available
            if 'condition_end_datetime' in relevant_events_filtered.columns:
                relevant_events_filtered = relevant_events_filtered[
                    (relevant_events_filtered['condition_end_datetime'].isnull()) | 
                    (relevant_events_filtered['condition_end_datetime'] >= relevant_events_filtered['time_0_dt'])
                ].copy()
            elif 'condition_era_end_datetime' in relevant_events_filtered.columns:
                relevant_events_filtered = relevant_events_filtered[
                    (relevant_events_filtered['condition_era_end_datetime'].isnull()) | 
                    (relevant_events_filtered['condition_era_end_datetime'] >= relevant_events_filtered['time_0_dt'])
                ].copy()

        elif lookback_strategy in ['recent_fixed', 'most_recent_fixed']:
            lookback_start_date = events_with_time_data['time_0_dt'] - pd.to_timedelta(lookback_window_days, unit='D')
            relevant_events_filtered = events_with_time_data[
                (events_with_time_data['event_datetime'] >= lookback_start_date) & 
                (events_with_time_data['event_datetime'] <= events_with_time_data['time_0_dt'])
            ].copy()
        else:
            logging.warning(f"Unsupported lookback strategy '{lookback_strategy}' for feature '{feature_name}'. Defaulting to all events before time_0.")
            relevant_events_filtered = events_with_time_data[events_with_time_data['event_datetime'] <= events_with_time_data['time_0_dt']].copy()

        
        # Consolidate values per person_id using vectorized operations
        feature_df_per_person_result = pd.DataFrame({'person_id': final_df['person_id'].unique(), feature_name: np.nan}) # Start with NaNs for all persons

        if not relevant_events_filtered.empty:
            relevant_events_filtered = relevant_events_filtered.sort_values(by=['person_id', 'event_datetime'], ascending=True)

            if feature_type_from_config == 'categorical':
                if consolidation_method == 'most_recent':
                    consolidated_series = relevant_events_filtered.groupby('person_id').last()['value']
                elif consolidation_method == 'most_frequent':
                    consolidated_series = relevant_events_filtered.groupby('person_id')['value'].apply(lambda x: x.mode().iloc[0] if not x.mode().empty else np.nan)
                else:
                    logging.warning(f"Unsupported consolidation method '{consolidation_method}' for categorical feature '{feature_name}'. Defaulting to most_recent.")
                    consolidated_series = relevant_events_filtered.groupby('person_id').last()['value']
            
            elif feature_type_from_config == 'binary':
                consolidated_series = relevant_events_filtered.groupby('person_id')['concept_id'].apply(lambda x: 1) # Just check presence
            
            elif feature_type_from_config == 'continuous':
                if consolidation_method == 'most_recent':
                    consolidated_series = relevant_events_filtered.groupby('person_id').last()['value']
                elif consolidation_method == 'average':
                    consolidated_series = relevant_events_filtered.groupby('person_id')['value'].mean()
                elif consolidation_method == 'max':
                    consolidated_series = relevant_events_filtered.groupby('person_id')['value'].max()
                elif consolidation_method == 'min':
                    consolidated_series = relevant_events_filtered.groupby('person_id')['value'].min()
                else:
                    logging.warning(f"Unsupported consolidation method '{consolidation_method}' for continuous feature '{feature_name}'. Defaulting to most_recent.")
                    consolidated_series = relevant_events_filtered.groupby('person_id').last()['value']
            
            else: # Fallback if type not explicitly handled
                logging.warning(f"Feature '{feature_name}' has unhandled type '{feature_type_from_config}'. Defaulting to binary presence.")
                consolidated_series = relevant_events_filtered.groupby('person_id')['concept_id'].apply(lambda x: 1) # Fallback to presence

            # Ensure consolidation results are in a DataFrame for merging
            if not consolidated_series.empty:
                # Apply clamping for BMI if needed (after consolidation)
                if feature_name == 'bmi' and pd.api.types.is_numeric_dtype(consolidated_series):
                    consolidated_series = np.clip(consolidated_series, 10.0, 60.0)

                feature_df_per_person_result = consolidated_series.reset_index(name=feature_name)
                # Merge into the final_df, ensuring all persons from final_df are kept
                final_df = pd.merge(final_df, feature_df_per_person_result[['person_id', feature_name]], on='person_id', how='left')
            else: # If consolidation resulted in empty series for some reason
                logging.warning(f"Consolidation for feature '{feature_name}' resulted in an empty series. Defaulting to NaN.")
                final_df[feature_name] = np.nan
        else: # If relevant_events_filtered was empty initially
            logging.warning(f"No relevant events found for feature '{feature_name}' after filtering. Defaulting to NaN.")
            final_df[feature_name] = np.nan


    logging.info(f"Final data shape after feature joining: {final_df.shape}")
    
    # Calculate age at time_0
    # Ensure 'birth_datetime' is not dropped until AFTER age_at_time_0 is calculated
    if 'birth_datetime' in final_df.columns and 'time_0_dt' in final_df.columns:
        # Removed format argument as it's not always consistent with BigQuery's output string format.
        # Pandas should generally infer it correctly.
        final_df['age_at_time_0'] = (final_df['time_0_dt'] - pd.to_datetime(final_df['birth_datetime']).dt.tz_localize(None)).dt.days / 365.25
        final_df['age_at_time_0'] = final_df['age_at_time_0'].astype(float).round(1)
    else:
        logging.warning("Cannot calculate 'age_at_time_0': 'birth_datetime' or 'time_0_dt' missing from final_df. Defaulting to NaN.")
        final_df['age_at_time_0'] = np.nan # Ensure column exists even if cannot calculate


    # Clean up temporary datetime columns and unused person columns
    final_df = final_df.drop(columns=[
        'time_0_dt', 'obs_end_dt', 'actual_outcome_dt', 'birth_datetime',
        'observation_period_start_date', 'observation_period_end_date', 'actual_outcome_datetime',
        'gender_concept_id', 'race_concept_id', 'ethnicity_concept_id', 'sex_at_birth_concept_id', # ethnicity/sex_at_birth are kept as names
        'age_at_consent', 'ehr_consent', 'has_ehr_data', 'year_of_birth'
    ], errors='ignore')
    
    return final_df
# --- build_person_base_query (remains mostly same, but ensures necessary cols) ---
def build_person_base_query(config: Dict[str, Any]) -> str:
    """
    Builds the base SQL query for the person table, incorporating cohort definition
    from the configuration.
    """
    cdr_path = get_aou_cdr_path()
    
    select_clauses = [
        "person.person_id",
        # We will calculate age relative to time_0 later in Python for consistency
        "person.birth_datetime", # Keep birth_datetime to calculate age at time_0
        "person.gender_concept_id",
        "p_gender_concept.concept_name as gender",
        "person.race_concept_id",
        "p_race_concept.concept_name as race",
        "person.ethnicity_concept_id",
        "p_ethnicity_concept.concept_name as ethnicity",
        "person.sex_at_birth_concept_id",
        "p_sex_at_birth_concept.concept_name as sex_at_birth",
        "cb_search_person.age_at_consent as age_at_consent", # Keep for info, not primary feature
        "cb_search_person.has_ehr_data as has_ehr_data",
        "CASE WHEN p_observation.observation_concept_id = 1586099 AND p_observation.value_source_value = 'ConsentPermission_Yes' THEN 'Yes' ELSE 'No' END AS ehr_consent",
        "person.year_of_birth"
    ]

    from_join_clauses = [
        f"FROM `{cdr_path}.person` person",
        f"LEFT JOIN `{cdr_path}.concept` p_gender_concept ON person.gender_concept_id = p_gender_concept.concept_id",
        f"LEFT JOIN `{cdr_path}.concept` p_race_concept ON person.race_concept_id = p_race_concept.concept_id",
        f"LEFT JOIN `{cdr_path}.concept` p_ethnicity_concept ON person.ethnicity_concept_id = p_ethnicity_concept.concept_id",
        f"LEFT JOIN `{cdr_path}.concept` p_sex_at_birth_concept ON person.sex_at_birth_concept_id = p_sex_at_birth_concept.concept_id",
        f"LEFT JOIN `{cdr_path}.cb_search_person` cb_search_person ON person.person_id = cb_search_person.person_id",
        f"LEFT JOIN `{cdr_path}.observation` p_observation ON person.person_id = p_observation.person_id AND p_observation.observation_concept_id = 1586099"
    ]

    where_conditions = []
    cohort_def = config.get('cohort_definition', {})

    cohort_table_id = cohort_def.get('cohort_table_id')
    if cohort_table_id:
        where_conditions.append(f"person.person_id IN (SELECT person_id FROM `{cdr_path}.{cohort_table_id}`)")
    else:
        # Placeholder for 'include_concepts' and 'exclude_concepts' from cohort_definition in config
        # For simplicity, base cohort will just be persons with EHR data for now.
        # If you add more cohort_definition logic to config.yaml, implement it here.
        where_conditions.append("cb_search_person.has_ehr_data = 1")
    
    # Add a minimum age filter, e.g., age >= 18
    # where_conditions.append("FLOOR(DATE_DIFF(DATE(CURRENT_DATE),DATE(person.birth_datetime), DAY)/365.25) >= 18")

    final_where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

    sql_query = f"""
    SELECT
        {', '.join(select_clauses)}
    {os.linesep.join(from_join_clauses)}
    {final_where_clause}
    """
    return sql_query
# Remaining helper functions (filter_columns, stratify_by_risk) are unchanged
def filter_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Filter dataframe to retain only specified columns."""
    missing_columns = [col for col in columns if col not in df.columns]
    if missing_columns:
        raise KeyError(f"Missing columns in DataFrame: {missing_columns}. Available columns: {list(df.columns)}")
    return df[columns].copy()
def stratify_by_risk(df: pd.DataFrame, risk_column: str, threshold: float) -> pd.DataFrame:
    """Stratify dataset into high vs. low risk groups based on threshold."""
    if risk_column not in df.columns:
        raise KeyError(f"Risk column '{risk_column}' does not exist in DataFrame.")
    if not pd.api.types.is_numeric_dtype(df[risk_column]):
        try:
            df[risk_column] = pd.to_numeric(df[risk_column], errors='coerce')
            if df[risk_column].isnull().all():
                raise ValueError(f"Risk column '{risk_column}' became all NaNs after conversion. It must contain numeric data.")
            logging.warning(f"Risk column '{risk_column}' was converted to numeric dtype.")
        except Exception:
            raise ValueError(f"Risk column '{risk_column}' must contain numeric data and could not be converted.")

    df = df.copy()
    df['risk_group'] = np.where(df[risk_column] >= threshold, 'high', 'low')
    df['risk_group'] = np.where(pd.isna(df[risk_column]), 'unknown', df['risk_group'])
    return df
if __name__ == "__main__":
    # This block is for direct testing of the dataloader.py script
    # It assumes environment variables are set and a config.yaml exists at root.
    # For local testing, ensure WORKSPACE_CDR and GOOGLE_CLOUD_PROJECT are mocked/set.
    
    # IMPORTANT: Adjust this path to your configuration.yaml if running directly
    config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configuration.yaml')
    
    # Mock AoU environment variables for local test (if not in Workbench)
    # Be sure to set these to valid values for your BigQuery project if testing
    # os.environ["WORKSPACE_CDR"] = "all-of-us-research-workbench-####.r2023q3_unzipped_data" 
    # os.environ["GOOGLE_CLOUD_PROJECT"] = "your-gcp-project-id" 
    
    if "WORKSPACE_CDR" not in os.environ or "GOOGLE_CLOUD_PROJECT" not in os.environ:
        logging.error("ERROR: WORKSPACE_CDR and GOOGLE_CLOUD_PROJECT environment variables MUST be set for dataloader.py to run directly.")
        logging.error("Please uncomment and set them in the script or ensure your environment is configured (e.g., in AoU Workbench).")
        exit() # Exit if environment not set for direct run

    try:
        logging.info("Starting direct dataloader.py execution...")
        config = load_configuration(config_file_path)
        logging.info("Configuration loaded successfully.")
        
        logging.info("Loading data from BigQuery with cohort construction and time_0 logic...")
        data_df = load_data_from_bigquery(config)
        
        logging.info(f"Data loaded from BigQuery. Shape: {data_df.shape}")
        if not data_df.empty:
            logging.info("First 5 rows of data:")
            logging.info(data_df.head().to_string()) # Use to_string for better logging
            logging.info("\nColumn names after loading:")
            logging.info(data_df.columns.tolist())
            logging.info(f"\nExample time_0: {data_df['time_0'].iloc[0]}")
            logging.info(f"Total events observed: {data_df['event_observed'].sum()}")
            logging.info(f"Median time to event/censoring: {data_df['time_to_event_days'].median()} days")
        else:
            logging.info("DataFrame is empty.")

    except RuntimeError as e:
        logging.error(f"A data loading or configuration error occurred: {e}")
    except KeyError as e:
        logging.error(f"A column or key error occurred: {e}. This might mean a concept was not found or mapped incorrectly.")
    except EnvironmentError as e:
        logging.error(f"Environment setup error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True) # Log full traceback       