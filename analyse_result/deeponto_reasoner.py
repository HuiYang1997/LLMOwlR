#!/usr/bin/env python3
"""
Advanced Description Logic Reasoner implementation using DeepOnto with ELK reasoner.
This can handle complex axioms including EL, ALC, and SHIQ features.
"""

import tempfile
import os
import re
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum
from deeponto.onto import Ontology

class AxiomType(Enum):
    SUBCLASS = "subclass"
    EQUIVALENCE = "equivalence"
    SUBPROPERTY = "subproperty"
    DOMAIN = "domain"
    RANGE = "range"

class DeepOntoDLReasoner:
    """A sophisticated DL reasoner using DeepOnto with ELK that can handle complex axioms."""
    
    def __init__(self):
        self.axioms = []
        
    def parse_complex_expression(self, expression: str) -> str:
        """Parse complex DL expressions and convert them to FSS format."""
        # Clean up the expression
        expression = expression.strip()
        
        # Handle equivalence axioms
        if "≡" in expression:
            left, right = expression.split("≡", 1)
            left = left.strip()
            right = right.strip()
            return f"EquivalentClasses({self._convert_expression_to_fss(left, right)})"
        
        # Handle subclass axioms
        if "⊑" in expression:
            left, right = expression.split("⊑", 1)
            left = left.strip()
            right = right.strip()
            return f"SubClassOf({self._convert_expression_to_fss(left, right)})"
        
        # Handle subproperty axioms
        if expression.startswith("SubObjectPropertyOf("):
            # Extract property names from SubObjectPropertyOf(A B)
            match = re.search(r'SubObjectPropertyOf\((\w+)\s+(\w+)\)', expression)
            if match:
                sub_prop, super_prop = match.groups()
                return f"SubObjectPropertyOf(:{sub_prop} :{super_prop})"
        
        return expression
    
    def extract_class_names(self, expression: str) -> Set[str]:
        """Extract all class names from a DL expression."""
        # Find all class names (A followed by numbers)
        class_names = set(re.findall(r'A\d+', expression))
        return class_names
    
    def extract_property_names(self, expression: str) -> Set[str]:
        """Extract all property names from a DL expression."""
        # Find all property names (r followed by numbers)
        property_names = set(re.findall(r'r\d+', expression))
        return property_names
    
    def create_ontology_from_axioms(self, axioms: List[str]):
        """Create an ontology from complex axioms and target conclusion."""
        try:
            # Write to temporary file
            with tempfile.NamedTemporaryFile("w", suffix=".owl", delete=False) as tmp:
                self.write_fss_ontology(axioms, tmp.name)
                fss_path = tmp.name
            
            # Debug: Print the FSS axioms being written
            # print(f"DEBUG: Creating ontology with {len(axioms)} axioms:")
            # for i, ax in enumerate(axioms):
            #     print(f"  {i+1}: {ax}")
            
            # # Debug: Print the file content
            # print(f"DEBUG: Created temporary file: {fss_path}")
            # with open(fss_path, 'r') as f:
            #     content = f.read()
            #     print(f"DEBUG: File content:\n{content}")
            
            # Load ontology with DeepOnto
            onto = Ontology(fss_path)
            
            # Store the path for cleanup
            self.fss_path = fss_path

            return onto
            
        except Exception as e:
            print(f"ERROR: Failed to create ontology")
            # print(f"ERROR: Axioms that caused the problem:")
            # for i, axiom in enumerate(axioms):
            #     print(f"  {i+1}: {axiom}")
            
            # # Try to get FSS axioms for debugging
            # try:
            #     fss_axioms = self.convert_symbolic_to_fss(axioms)
            #     print(f"ERROR: FSS axioms that caused the problem:")
            #     for i, fss_ax in enumerate(fss_axioms):
            #         print(f"  {i+1}: {fss_ax}")
            # except Exception as fss_error:
            #     print(f"ERROR: Could not convert to FSS format: {fss_error}")
    
    def add_axiom(self, axiom_str: str):
        """Add a single axiom to the ontology."""
        axiom_str = axiom_str.strip()
        
        # Convert to FSS format and add to axioms list
        fss_axiom = self.parse_complex_expression(axiom_str)
        self.axioms.append(fss_axiom)
        
        print(f"Loaded axiom: {axiom_str}")
    
    def split_top_level(self, expr: str, operator: str) -> list:
        """Split expression by operator at top level (not inside parentheses or quantifiers)."""
        parts = []
        current = ''
        paren = 0
        i = 0
        while i < len(expr):
            c = expr[i]
            if c == '(':
                paren += 1
            elif c == ')':
                paren -= 1
            elif c == operator and paren == 0:
                parts.append(current.strip())
                current = ''
                i += 1
                continue
            current += c
            i += 1
        if current:
            parts.append(current.strip())
        return parts

    def parse_class_expression(self, expression: str, depth: int = 0):
        """Parse a class expression and return the corresponding FSS format."""
        # Add debug information
        if depth > 0:
            print(f"DEBUG: Parsing at depth {depth}: {expression}")
            
        # Limit recursion depth to avoid stack overflow
        if depth > 20:
            print(f"Warning: Maximum recursion depth ({depth}) reached while parsing: {expression}")
            return None
            
        # Handle None or empty expressions
        if not expression:
            return None
            
        # Parenthesized
        if expression.startswith('(') and expression.endswith(')'):
            # Only strip one pair of parentheses
            result = self.parse_class_expression(expression[1:-1], depth + 1)
            return result

        # Existential restriction: ∃r.C (C can be nested)
        m = re.match(r'^∃([^.]+)\.(.+)$', expression)
        if m:
            prop_name = m.group(1).strip()
            rest = m.group(2).strip()
            
            # If rest is parenthesized, parse as a complex class expression
            if rest.startswith('(') and rest.endswith(')'):
                target_class = self.parse_class_expression(rest[1:-1], depth + 1)
            else:
                target_class = self.parse_class_expression(rest, depth + 1)
            
            if target_class:
                return f"ObjectSomeValuesFrom(:{prop_name} {target_class})"
            else:
                return None

        # Universal restriction: ∀r.C (C can be nested)
        m = re.match(r'^∀([^.]+)\.(.+)$', expression)
        if m:
            prop_name = m.group(1).strip()
            rest = m.group(2).strip()
            
            if rest.startswith('(') and rest.endswith(')'):
                target_class = self.parse_class_expression(rest[1:-1], depth + 1)
            else:
                target_class = self.parse_class_expression(rest, depth + 1)
            
            if target_class:
                return f"ObjectAllValuesFrom(:{prop_name} {target_class})"
            else:
                return None

        # Simple class name
        if re.match(r'^A\d+$', expression):
            return f":{expression}"

        # Intersection: A ⊓ B ⊓ ... (handle this first for proper precedence)
        if '⊓' in expression:
            parts = self.split_top_level(expression, '⊓')
            classes = []
            for part in parts:
                parsed = self.parse_class_expression(part.strip(), depth + 1)
                if parsed:
                    classes.append(parsed)
            if len(classes) == 1:
                result = classes[0]
            elif len(classes) > 1:
                result = f"ObjectIntersectionOf({' '.join(classes)})"
            else:
                result = None
            return result
                
        # If we get here, we couldn't parse the expression
        print(f"Warning: Could not parse class expression: {expression}")
        return None
    
    def check_subsumption(self, axioms: List[str], target_conclusion: str) -> bool:
        """Check if the target conclusion follows from the axioms."""
        # Create a fresh ontology each time to avoid inheritance cycles
        # Reset the reasoner state completely
        self.axioms = []
        
        if "⊑" not in target_conclusion:
            print(f"Treat as false by default as the target conlusion do not contain ⊑:\n (premise) {axioms}\n (conclusion) {target_conclusion}")
            return False

        left, right = target_conclusion.split("⊑", 1)
        left = left.strip()
        right = right.strip()
        
        # Extract all concept names from the conclusion
        import re
        conclusion_concepts = set(re.findall(r'A\d+', target_conclusion))
        
        # Find axioms that define concepts mentioned in the conclusion
        missing_definitions = []
        for concept in conclusion_concepts:
            concept_defined = False
            for axiom in axioms:
                # Check if this axiom defines the concept (appears on left side)
                if f"{concept} " in axiom and ("⊑" in axiom or "≡" in axiom):
                    concept_defined = True
                    break
            if not concept_defined:
                # Add a minimal definition for the concept
                missing_definitions.append(f"{concept} ⊑ {concept}")
        
        # Add missing definitions to axioms
        enhanced_axioms = axioms + missing_definitions
        
        # Check if the conclusion is simple (no complex expressions)
        if not self.is_complex_expression(left) and not self.is_complex_expression(right):
            # Simple case - no transformation needed
            onto = self.create_ontology_from_axioms(enhanced_axioms)
            iri_prefix = "http://example.org/"
            sub_iri = iri_prefix + left
            super_iri = iri_prefix + right
            try:
                sub_entity = onto.get_owl_object(sub_iri)
                super_entity = onto.get_owl_object(super_iri)
                entailed = onto.reasoner.check_subsumption(sub_entity, super_entity)
            except Exception as e:
                # print(f"Error in check_subsumption: {e}")
                entailed = False
        else:
            # Complex case - need transformation
            transformed_axioms, transformed_left, transformed_right = self.transform_complex_conclusion(
                enhanced_axioms, left, right
            )
            # Create ontology with transformed axioms
            onto = self.create_ontology_from_axioms(transformed_axioms)
            # Use DeepOnto's check_subsumption method with entity objects
            iri_prefix = "http://example.org/"
            sub_iri = iri_prefix + transformed_left
            super_iri = iri_prefix + transformed_right
            try:
                sub_entity = onto.get_owl_object(sub_iri)
                super_entity = onto.get_owl_object(super_iri)
                entailed = onto.reasoner.check_subsumption(sub_entity, super_entity)
            except Exception as e:
                # print(f"Error in check_subsumption: {e}")
                entailed = False
            
        # Clean up
        if hasattr(self, 'fss_path'):
            os.remove(self.fss_path)
        
        return entailed
        
    
    def is_complex_expression(self, expression: str) -> bool:
        """Check if an expression is complex (contains ∃, ⊓, ⊔, etc.)."""
        complex_indicators = ['∃', '⊓', '⊔', '∀', '(', ')']
        return any(indicator in expression for indicator in complex_indicators)
    
    def transform_complex_conclusion(self, original_axioms: List[str], left_class: str, right_class: str) -> tuple:
        """Transform a complex conclusion into a simple one using new atomic concepts."""
        new_axioms = []
        
        # Check if left side is complex
        if self.is_complex_expression(left_class):
            left_new_concept = self.generate_new_concept_name(1)
            new_axioms.append(f"{left_new_concept} ≡ {left_class}")
            simple_left = left_new_concept
        else:
            simple_left = left_class
        
        # Check if right side is complex
        if self.is_complex_expression(right_class):
            right_new_concept = self.generate_new_concept_name(2)
            new_axioms.append(f"{right_new_concept} ≡ {right_class}")
            simple_right = right_new_concept
        else:
            simple_right = right_class
        
        # Combine original axioms with the new axioms
        transformed_axioms = original_axioms + new_axioms
        
        # Print transformation details if either side was complex
        # if self.is_complex_expression(left_class) or self.is_complex_expression(right_class):
        #     print(f"Transformed complex conclusion:")
        #     print(f"  Original: {left_class} ⊑ {right_class}")
        #     print(f"  New axioms: {new_axioms}")
        #     print(f"  Simple conclusion: {simple_left} ⊑ {simple_right}")
        
        return transformed_axioms, simple_left, simple_right
    
    def generate_new_concept_name(self, i) -> str:
        """Generate a new atomic concept name (A0, A00, etc.)."""
        # Try A0, A00, A000, etc.
        name = "A" + "0" * i
        return name
    
    def check_step_correctness(self, premises: List[str], conclusion: str, all_axioms: List[str]) -> str:
        """Check if a derivation step is correct."""
        # Convert premise references to actual axioms
        actual_premises = []
        for premise in premises:
            if premise.isdigit():
                # It's an axiom index
                idx = int(premise)
                if 0 <= idx < len(all_axioms):
                    actual_premises.append(all_axioms[idx])
            elif premise.startswith("STEP"):
                # It's a previous step - include it as a premise
                # For now, we'll treat STEP references as valid premises
                # since they represent intermediate conclusions
                actual_premises.append(premise)
            else:
                # It's already an axiom string
                actual_premises.append(premise)
        
        # Add explicit decomposition axioms for complex equivalence axioms
        enhanced_premises = []
        for premise in actual_premises:
            enhanced_premises.append(premise)
            # If it's an equivalence axiom with complex right side, add decomposition axioms
            if '≡' in premise and '⊓' in premise:
                left, right = premise.split('≡', 1)
                left = left.strip()
                right = right.strip()
                
                # Add the left-to-right subsumption
                enhanced_premises.append(f"{left} ⊑ {right}")
                
                # If right side has existential quantifiers, add explicit decomposition
                if '∃' in right:
                    # Extract existential parts and add them as separate axioms
                    import re
                    existential_parts = re.findall(r'∃[^⊓⊔]+', right)
                    for part in existential_parts:
                        enhanced_premises.append(f"{left} ⊑ {part}")
        
        # Extract all concept names from the conclusion
        import re
        conclusion_concepts = set(re.findall(r'A\d+', conclusion))
        
        # Find axioms that define concepts mentioned in the conclusion
        missing_definitions = []
        for concept in conclusion_concepts:
            concept_defined = False
            for axiom in all_axioms:
                # Check if this axiom defines the concept (appears on left side)
                if f"{concept} " in axiom and ("⊑" in axiom or "≡" in axiom):
                    concept_defined = True
                    break
            if not concept_defined:
                # Add a minimal definition for the concept
                missing_definitions.append(f"{concept} ⊑ {concept}")
        
        # Add missing definitions to enhanced premises
        enhanced_premises.extend(missing_definitions)
        
        # First check if the conclusion follows from the enhanced premises
        if enhanced_premises:
            follows_from_premises = self.check_subsumption(enhanced_premises, conclusion)
            if follows_from_premises:
                return "totally_correct"
        
        # If not totally correct, check if it follows from all axioms
        follows_from_all = self.check_subsumption(all_axioms, conclusion)
        if follows_from_all:
            return "partially_correct"
        else:
            return "incorrect"
    
    def check_simplification_correctness(self, original_axiom: str, simplified_axiom: str) -> bool:
        """Check if a simplified axiom follows from the original axiom."""
        try:
            return self.check_subsumption([original_axiom], simplified_axiom)
        except Exception as e:
            print(f"Error checking simplification correctness: {e}")
            return False
    
    # def check_axiom_equivalence(self, axiom1: str, axiom2: str) -> bool:
    #     """Check if two axioms are logically equivalent."""
    #     # Check if axiom1 implies axiom2
    #     implies_forward = self.check_subsumption([axiom1], axiom2)
        
    #     # Check if axiom2 implies axiom1
    #     implies_backward = self.check_subsumption([axiom2], axiom1)
        
    #     # Both directions must hold for equivalence
    #     return implies_forward and implies_backward
    
    def print_inferred_hierarchy(self):
        """Print the inferred subclass hierarchy for debugging."""
        if not self.onto:
            print("No ontology loaded.")
            return
        print("\nInferred subclass hierarchy:")
        # DeepOnto doesn't have a direct way to print hierarchy like owlready2
        # This would need to be implemented differently
        print("Hierarchy printing not implemented for DeepOnto")
    
    # FSS conversion methods (from original DeepOntoReasoner)
    def convert_symbolic_to_fss(self, axioms: List[str]) -> List[str]:
        """Convert symbolic DL axioms to FSS format."""
        fss_axioms = []
        
        for axiom in axioms:
            # remove the content of the form '('+letters only+')'
            axiom = re.sub(r'\([a-zA-Z\s]+\)', '', axiom)

            # Handle subclass axioms: A ⊑ B
            if "⊑" in axiom and "≡" not in axiom:
                left, right = axiom.split("⊑", 1)
                left = left.strip()
                right = right.strip()
                
                # Convert to FSS format
                fss_axiom = self._convert_expression_to_fss(left, right)
                fss_axioms.append(f"SubClassOf({fss_axiom})")
                
            # Handle equivalence axioms: A ≡ B
            elif "≡" in axiom:
                left, right = axiom.split("≡", 1)
                left = left.strip()
                right = right.strip()
                
                fss_left = self._convert_complex_expression_to_fss(left)
                fss_right = self._convert_complex_expression_to_fss(right)
                fss_axioms.append(f"EquivalentClasses({fss_left} {fss_right})")
                
        # print("fss_axioms", fss_axioms)
        return fss_axioms
    
    def _convert_expression_to_fss(self, left: str, right: str) -> str:
        """Convert a DL expression to FSS format."""
        # Handle simple class names
        if re.match(r'^A\d+$', left):
            left_fss = f":{left}"
        else:
            left_fss = self._convert_complex_expression_to_fss(left)
            
        if re.match(r'^A\d+$', right):
            right_fss = f":{right}"
        else:
            right_fss = self._convert_complex_expression_to_fss(right)
            
        return f"{left_fss} {right_fss}"
    
    def _convert_complex_expression_to_fss(self, expression: str) -> str:
        """Convert complex DL expressions to FSS format using robust parsing (handles nesting)."""
        expression = expression.strip()
        # Parenthesized
        if expression.startswith('(') and expression.endswith(')'):
            return self._convert_complex_expression_to_fss(expression[1:-1])
        
        # Check for existential restriction: ∃r.C or ∃r.(C ⊓ D)
        if expression.startswith('∃'):
            # Find the dot after ∃
            dot_pos = expression.find('.', 1)  # Start after ∃
            if dot_pos > 0:
                prop_name = expression[1:dot_pos].strip()
                rest = expression[dot_pos+1:].strip()
                
                # Check if rest is parenthesized
                if rest.startswith('(') and rest.endswith(')'):
                    # ∃r.(C ⊓ D) - existential with complex content inside
                    inner_content = rest[1:-1].strip()
                    inner_fss = self._convert_complex_expression_to_fss(inner_content)
                    return f"ObjectSomeValuesFrom(:{prop_name} {inner_fss})"
                else:
                    # ∃r.C - simple existential
                    # Check if rest contains top-level operators
                    if '⊓' in rest or '⊔' in rest:
                        # Check if it's actually ∃r.C ⊓ D (intersection at top level)
                        # vs ∃r.(C ⊓ D) (intersection inside existential)
                        # We need to check if the ⊓ is at the top level of the entire expression
                        if '⊓' in expression:
                            # This might be ∃r.C ⊓ D, not ∃r.(C ⊓ D)
                            # Let the top-level intersection handler deal with it
                            pass
                        else:
                            # It's ∃r.C where C is complex
                            return f"ObjectSomeValuesFrom(:{prop_name} {self._convert_complex_expression_to_fss(rest)})"
                    else:
                        # Simple existential: ∃r.C
                        return f"ObjectSomeValuesFrom(:{prop_name} {self._convert_complex_expression_to_fss(rest)})"
        
        # Universal restriction: ∀r.C
        if expression.startswith('∀'):
            m = re.match(r'^∀([^.]+)\.(.+)$', expression)
            if m:
                prop_name = m.group(1).strip()
                rest = m.group(2).strip()
                return f"ObjectAllValuesFrom(:{prop_name} {self._convert_complex_expression_to_fss(rest)})"
        
        # Negation
        if expression.startswith('¬'):
            return f"ObjectComplementOf({self._convert_complex_expression_to_fss(expression[1:].strip())})"
        
        # Union (⊔) at top level
        if '⊔' in expression:
            parts = self.split_top_level(expression, '⊔')
            if len(parts) > 1:
                fss_parts = [self._convert_complex_expression_to_fss(part) for part in parts]
                return f"ObjectUnionOf({' '.join(fss_parts)})"
        
        # Intersection (⊓) at top level
        if '⊓' in expression:
            parts = self.split_top_level(expression, '⊓')
            if len(parts) > 1:
                fss_parts = [self._convert_complex_expression_to_fss(part) for part in parts]
                return f"ObjectIntersectionOf({' '.join(fss_parts)})"
        
        # Simple class name
        if re.match(r'^A\d+$', expression):
            return f":{expression}"
        
        # Check if it's an existential quantifier that wasn't caught by the regex
        if '∃' in expression and '.' in expression:
            # Try to parse it manually
            try:
                # Find the first dot after ∃
                dot_pos = expression.find('.', expression.find('∃'))
                if dot_pos > 0:
                    prop_part = expression[expression.find('∃')+1:dot_pos].strip()
                    rest_part = expression[dot_pos+1:].strip()
                    return f"ObjectSomeValuesFrom(:{prop_part} {self._convert_complex_expression_to_fss(rest_part)})"
            except:
                pass
        
        # Fallback: treat as atomic
        return f":{expression}"
    
    def write_fss_ontology(self, axioms: List[str], fss_path: str):
        """Write axioms in FSS format to a file."""
        fss_axioms = self.convert_symbolic_to_fss(axioms)
        with open(fss_path, "w") as f:
            f.write("Prefix(:=<http://example.org/>)\n")
            f.write("Ontology(<http://example.org/ontology>\n")
            for ax in fss_axioms:
                f.write(f"  {ax}\n")
                # print(f"DEBUG: Writing axiom: {ax}")
            f.write(")\n")
        # input("Press Enter to continue...")

def test_deeponto_reasoner():
    """Test the DeepOnto reasoner with various examples."""
    print("Testing DeepOnto Reasoner...")
    
    reasoner = DeepOntoDLReasoner()
    
    # Test 1: Simple transitivity
    axioms = ["A1 ⊑ A2", "A2 ⊑ A8"]
    conclusion = "A1 ⊑ A8"
    result = reasoner.check_subsumption(axioms, conclusion)
    print(f"Test 1 - Does {conclusion} follow from axioms? {result}")
    
    # Test 2: Existential quantifier
    axioms = ["A1 ⊑ A2 ⊓ ∃r3.A4", "A2 ⊑ A8"]
    conclusion = "A1 ⊑ A8"
    result = reasoner.check_subsumption(axioms, conclusion)
    print(f"Test 2 - Does {conclusion} follow from axioms with existential? {result}")
    
    # Test 3: Equivalence
    axioms = ["A1 ≡ A2 ⊓ A3", "A2 ⊑ A8"]
    conclusion = "A1 ⊑ A8"
    result = reasoner.check_subsumption(axioms, conclusion)
    print(f"Test 3 - Does {conclusion} follow from equivalence axioms? {result}")
    
    # Test 4: Complex nested axiom
    print("\nTesting with a complex nested axiom:")
    nested_axiom = "A28 ≡ A12 ⊓ ∃r3.(∃r4.A5 ⊓ ∃r9.A16) ⊓ ∃r3.∃r6.A7"
    reasoner2 = DeepOntoDLReasoner()
    try:
        reasoner2.create_ontology_from_axioms([nested_axiom], "")
        print(f"Successfully parsed and added: {nested_axiom}")
    except Exception as e:
        print(f"Failed to parse complex axiom: {e}")
    
    return reasoner

if __name__ == "__main__":
    test_deeponto_reasoner() 