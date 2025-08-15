#!/usr/bin/env Rscript

# CHARMTwinsights Model Template - R
# Replace this template with your actual model implementation.

suppressPackageStartupMessages({
  library(jsonlite)
  library(readr)
  # Add your model library imports here
  # library(randomForest)
  # library(caret)
  # library(e1071)
})

load_model <- function() {
  # Load your trained model from file
  # Examples:
  # return(readRDS("model.rds"))
  # load("model.RData")  # loads objects into environment
  # return(model_object)
  
  # Dummy model for template
  dummy_model <- list(
    predict = function(x) {
      # Replace with actual prediction logic
      return(runif(nrow(x)))
    }
  )
  
  return(dummy_model)
}

preprocess_input <- function(input_data) {
  # Convert input to data frame
  df <- if (is.list(input_data) && !is.data.frame(input_data)) {
    do.call(rbind, lapply(input_data, as.data.frame))
  } else {
    as.data.frame(input_data)
  }
  
  # Add your preprocessing steps here:
  # - Handle missing values
  # - Scale/normalize features  
  # - Encode categorical variables
  # - Feature selection/engineering
  
  return(df)
}

postprocess_output <- function(predictions, input_data) {
  # Convert predictions to desired format
  results <- list()
  
  for (i in seq_along(predictions)) {
    result <- list(
      prediction = as.numeric(predictions[i])
      # Add any additional output fields
      # confidence = as.numeric(confidence[i]),
      # probability = as.numeric(probability[i])
    )
    
    # Include input ID if provided
    if (is.list(input_data) && length(input_data) >= i) {
      if ("id" %in% names(input_data[[i]])) {
        result$id <- input_data[[i]]$id
      }
    } else if ("id" %in% names(input_data)) {
      result$id <- input_data$id
    }
    
    results[[i]] <- result
  }
  
  return(results)
}

main <- function() {
  # Parse command line arguments
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) < 1 || length(args) > 2) {
    cat("Usage: predict.R <input.json> [output.json]\n", file = stderr())
    quit(status = 1)
  }
  
  input_file <- args[1]
  output_file <- if (length(args) == 2) args[2] else NULL
  
  tryCatch({
    cat("Loading R model...\n", file = stderr())
    model <- load_model()
    
    # Load input data
    input_data <- fromJSON(input_file)
    
    record_count <- if (is.list(input_data) && !is.data.frame(input_data)) {
      length(input_data)
    } else {
      1
    }
    
    cat(sprintf("Processing %d record(s)\n", record_count), file = stderr())
    
    # Preprocess input
    processed_data <- preprocess_input(input_data)
    
    # Make predictions
    predictions <- model$predict(processed_data)
    
    # Postprocess output
    results <- postprocess_output(predictions, input_data)
    
    cat(sprintf("Generated %d prediction(s)\n", length(results)), file = stderr())
    
    # Output results
    if (!is.null(output_file)) {
      # New file-based I/O pattern
      write_json(results, output_file, pretty = TRUE)
      cat(sprintf("Results written to %s\n", output_file))
    } else {
      # Legacy stdout pattern for backwards compatibility
      cat(toJSON(results, auto_unbox = TRUE))
    }
    
  }, error = function(e) {
    cat(sprintf("Error during prediction: %s\n", e$message), file = stderr())
    quit(status = 1)
  })
}

# Run main function
main()