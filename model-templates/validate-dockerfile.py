#!/usr/bin/env python3
"""
CHARMTwinsights Dockerfile Validator

This script checks your model's Dockerfile for common mistakes that would
break integration with the model server.
"""
import sys
import re
from pathlib import Path

class DockerfileValidator:
    def __init__(self, dockerfile_path):
        self.dockerfile_path = Path(dockerfile_path)
        self.errors = []
        self.warnings = []
        
    def validate(self):
        """Run all validation checks"""
        if not self.dockerfile_path.exists():
            self.errors.append(f"Dockerfile not found: {self.dockerfile_path}")
            return False
            
        content = self.dockerfile_path.read_text()
        
        self._check_cmd_entrypoint(content)
        self._check_workdir(content)
        self._check_predict_script(content)
        self._check_metadata_files(content)
        self._check_common_issues(content)
        
        return len(self.errors) == 0
    
    def _check_cmd_entrypoint(self, content):
        """Check for forbidden CMD/ENTRYPOINT directives"""
        cmd_pattern = r'^\s*(CMD|ENTRYPOINT)\s+'
        matches = re.findall(cmd_pattern, content, re.MULTILINE | re.IGNORECASE)
        
        if matches:
            self.errors.append(
                "❌ CRITICAL: Found CMD or ENTRYPOINT directive(s). "
                "These must be removed for CHARMTwinsights compatibility. "
                "The model server handles execution automatically."
            )
    
    def _check_workdir(self, content):
        """Check for proper WORKDIR setting"""
        workdir_pattern = r'^\s*WORKDIR\s+(.+)'
        matches = re.findall(workdir_pattern, content, re.MULTILINE | re.IGNORECASE)
        
        if not matches:
            self.warnings.append(
                "⚠️  No WORKDIR found. Consider adding 'WORKDIR /app' for consistency."
            )
        elif '/app' not in matches[-1]:  # Check last WORKDIR
            self.warnings.append(
                f"⚠️  WORKDIR is '{matches[-1].strip()}'. "
                f"Consider using '/app' for consistency with templates."
            )
    
    def _check_predict_script(self, content):
        """Check for predict script setup"""
        chmod_pattern = r'RUN\s+chmod\s+\+x\s+.*predict'
        
        if not re.search(chmod_pattern, content, re.IGNORECASE):
            self.warnings.append(
                "⚠️  No 'chmod +x predict' found. Make sure your predict script is executable."
            )
    
    def _check_metadata_files(self, content):
        """Check for metadata files (optional but recommended)"""
        has_readme = re.search(r'COPY.*README\.md', content, re.IGNORECASE)
        has_examples = re.search(r'COPY.*examples\.json', content, re.IGNORECASE)
        
        if not has_readme:
            self.warnings.append(
                "💡 Consider adding 'COPY README.md ./' for container-based documentation."
            )
            
        if not has_examples:
            self.warnings.append(
                "💡 Consider adding 'COPY examples.json ./' for container-based examples."
            )
    
    def _check_common_issues(self, content):
        """Check for other common issues"""
        # Check for EXPOSE (usually not needed)
        if re.search(r'^\s*EXPOSE\s+', content, re.MULTILINE | re.IGNORECASE):
            self.warnings.append(
                "⚠️  EXPOSE directive found. Usually not needed for CHARMTwinsights models."
            )
        
        # Check for USER directive (can cause permission issues)
        if re.search(r'^\s*USER\s+', content, re.MULTILINE | re.IGNORECASE):
            self.warnings.append(
                "⚠️  USER directive found. This might cause permission issues with shared volumes."
            )
    
    def print_results(self):
        """Print validation results"""
        print(f"\n🔍 Dockerfile Validation: {self.dockerfile_path}")
        print("=" * 60)
        
        if self.errors:
            print("\n❌ ERRORS (must fix):")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS (recommended fixes):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ Dockerfile looks good!")
        
        print("\n" + "=" * 60)
        
        if self.errors:
            print("❌ Validation FAILED - fix errors before proceeding")
            return False
        else:
            print("✅ Validation PASSED")
            return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python validate-dockerfile.py <path-to-Dockerfile>")
        print("\nExample:")
        print("  python validate-dockerfile.py ./Dockerfile")
        print("  python validate-dockerfile.py ../my-model/Dockerfile")
        sys.exit(1)
    
    dockerfile_path = sys.argv[1]
    validator = DockerfileValidator(dockerfile_path)
    
    success = validator.validate()
    validator.print_results()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
