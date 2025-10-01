import json
import re
import sys
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from deeponto_reasoner import DeepOntoDLReasoner

class StepCorrectness(Enum):
    TOTALLY_CORRECT = "totally_correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"

@dataclass
class Axiom:
    id: int
    original: str
    simplified: str

@dataclass
class DerivationStep:
    step_id: str
    premises: List[str]
    conclusion: str
    explanation: str
    correctness: StepCorrectness

@dataclass
class ProofTree:
    conclusion: str
    premises: List[str]
    children: List['ProofTree']
    step_id: Optional[str] = None

class ReasoningAnalyzer:
    def __init__(self):
        self.axioms: Dict[int, Axiom] = {}
        self.steps: List[DerivationStep] = []
        self.target_conclusion: str = ""
        
    def check_simplified_axioms_inference(self, simplified_axioms: Dict[str, str], target_conclusion: str) -> bool:
        """Check if the simplified axioms can derive the target conclusion using the reasoner.
        
        Args:
            simplified_axioms: Dictionary mapping axiom IDs to their simplified forms
            target_conclusion: The target conclusion to derive
            
        Returns:
            True if the simplified axioms can derive the target conclusion, False otherwise
        """
        if not simplified_axioms or not target_conclusion:
            return False
        
        all_axioms = []
        # Collect all simplified axioms as strings
        for axiom in list(simplified_axioms.values()):
            # split axioms if it contains "," or "and"
            if "," in axiom:
                all_axioms.extend([a.strip() for a in axiom.split(",")])
            elif "and" in axiom:
                all_axioms.extend([a.strip() for a in axiom.split("and")])
            else:
                all_axioms.append(axiom)
        
        # Use the reasoner to check if the simplified axioms can derive the target conclusion
        reasoner = DeepOntoDLReasoner()
        can_derive = reasoner.check_subsumption(all_axioms, target_conclusion)

        return can_derive
        
    def calculate_jaccard_similarity(self, set1: Set[int], set2: Set[int]) -> float:
        """Calculate Jaccard similarity between two sets.
        Jaccard similarity is defined as the size of the intersection divided by the size of the union.
        """
        if not set1 and not set2:  # Both sets are empty
            return 1.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union
        
    def load_json_file(self, file_path: str) -> Dict:
        """Load and parse the JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_axioms_from_prompt(self, prompt: str) -> Dict[int, Axiom]:
        """Extract axioms from the prompt text."""
        axioms = {}
        
        # Find the axioms section in the prompt
        axiom_pattern = r'\((\d+)\)\s+([^\n]+)'
        matches = re.findall(axiom_pattern, prompt)
        
        for match in matches:
            axiom_id = int(match[0])
            axiom_text = match[1].strip()
            axioms[axiom_id] = Axiom(
                id=axiom_id,
                original=axiom_text,
                simplified=axiom_text  # Initially same as original
            )
        
        return axioms
    
    def extract_target_conclusion(self, prompt: str) -> str:
        """Extract the target conclusion from the prompt."""
        conclusion_pattern = r'\*\*Target Conclusion:\*\*\s*([^\n]+)'
        match = re.search(conclusion_pattern, prompt)
        if match:
            conclusion = match.group(1).strip()
            # Convert ⊒ to ⊑ by reversing the order: "C ⊒ D" -> "D ⊑ C"
            if '⊒' in conclusion:
                conclusion = re.sub(r'([^⊒]+)\s*⊒\s*([^⊒]+)', r'\2 ⊑ \1', conclusion)
            return conclusion
        return ""
    
    def extract_reasoning_dsl(self, response: str) -> str:
        """Extract the reasoning-dsl block from the response. If not found, try to extract from AXIOMS_USED, SIMPLIFY, DERIVE."""
        # Try to find code block first
        import re
        code_block = re.search(r'```reasoning-dsl\n(.*?)```', response, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        
        # Fallback: try to find from AXIOMS_USED onwards
        # Find the first occurrence of AXIOMS_USED
        start = None
        for key in ["AXIOMS_USED:", "AXIOMS_USED :", "AXIOMS_USED"]:
            idx = response.find(key)
            if idx != -1:
                start = idx
                break
        if start is None:
            return None
        # Try to find the end: either next code block, or end of string
        end = None
        for key in ["\n\n", "\n#", "\n##", "\n*", "\nModel:", "\nExplanation:"]:
            idx = response.find(key, start)
            if idx != -1:
                end = idx
                break
        if end is None:
            end = len(response)
        # Extract the block
        dsl_text = response[start:end].strip()
        # If it looks like it contains the right sections, return it
        if ("AXIOMS_USED" in dsl_text and "DERIVE" in dsl_text):
            return dsl_text
        # Otherwise, try to extract lines containing AXIOMS_USED, SIMPLIFY, DERIVE and following lines
        lines = response.splitlines()
        dsl_lines = []
        in_dsl = False
        for line in lines:
            if any(k in line for k in ["AXIOMS_USED", "SIMPLIFY", "DERIVE", "STEP", "EXPLANATION:"]):
                in_dsl = True
            if in_dsl:
                dsl_lines.append(line)
        if dsl_lines:
            return "\n".join(dsl_lines)

    
    def parse_reasoning_dsl(self, dsl_text: str) -> Tuple[List[int], Dict[str, str], List[DerivationStep]]:
        """Parse the reasoning-dsl format."""
        axioms_used = []
        simplifications = {}
        steps = []
        
        lines = dsl_text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            if line.startswith('AXIOMS_USED:'):
                current_section = 'axioms_used'
                # Parse axioms used
                axioms_part = line.split(':', 1)[1].strip().replace('[', '').replace(']', '')
                try:
                    axioms_used = [int(x.strip()) for x in axioms_part.split(',')]
                except:
                    axioms_used = []
                continue
            elif line.startswith('SIMPLIFY:'):
                current_section = 'simplify'     
                continue
            elif line.startswith('DERIVE:'):
                current_section = 'derive'
                continue
            elif line.startswith('STEP'):
                current_section = 'step'
                # Parse step
                step_match = re.match(r'STEP\s*(?:\[)?(\d+)(?:\])?:\s*(?:\[)?(.*?)(?:\])?\s*(?:->|→)\s*(.*?)$', line)
                if step_match:
                    step_num = step_match.group(1)
                    premises_str = step_match.group(2)
                    conclusion = step_match.group(3)
                    # remove the content of the form '('+letters only+')'
                    conclusion = re.sub(r'\([a-zA-Z\s]+\)', '', conclusion).strip()
            
                    
                    # Convert ⊒ to ⊑ by reversing the order: "C ⊒ D" -> "D ⊑ C"
                    if '⊒' in conclusion:
                        conclusion = re.sub(r'([^⊒]+)\s*⊒\s*([^⊒]+)', r'\2 ⊑ \1', conclusion)
                    
                    # Clean up malformed conclusions that contain extra symbols
                    # Remove any content after → or ≡ that shouldn't be in the conclusion
                    if '→' in conclusion:
                        conclusion = conclusion.split('→')[0].strip()
                    if '≡' in conclusion and '⊑' not in conclusion:
                        # If it's an equivalence, convert to subsumption for processing
                        parts = conclusion.split('≡', 1)
                        if len(parts) == 2:
                            conclusion = f"{parts[0].strip()} ⊑ {parts[1].strip()}"
                    
                    # Handle multiple conclusions separated by "and"
                    if ' and ' in conclusion:
                        # Take only the first conclusion for simplicity
                        conclusion = conclusion.split(' and ')[0].strip()
                    
                    # Parse premises
                    premises = [p.strip() for p in premises_str.split(',')]
                    
                    # Create step object
                    step = DerivationStep(
                        step_id=f"STEP{step_num}",
                        premises=premises,
                        conclusion=conclusion,
                        explanation="",
                        correctness=StepCorrectness.INCORRECT
                    )
                    steps.append(step)
                continue
            elif line.startswith('EXPLANATION:'):
                if steps:
                    # Add explanation to the last step
                    explanation = line.split(':', 1)[1].strip()
                    steps[-1].explanation = explanation
                continue
            elif current_section == 'simplify' and (line.startswith('[') or line.startswith('(') or re.match(r'^\d+[:\.]', line)):
                # Parse simplification
                # Try to match any separator between original and simplified
                # Match both formats: with arrow (->|→) and without arrow
                match = re.match(r'^\s*(?:\[|\()?(\d+)(?:\]|\))?(?::|\.|\ )\s*(.*?)(?:\s*(?:->|→)\s*(.*?))?$', line)
                
                if match:
                    axiom_id = match.group(1)
                    original = match.group(2).strip()
                    simplified = match.group(3).strip() if match.group(3) else original  

                                        
                    # Skip empty simplified forms
                    if not simplified or simplified.strip() == '':
                        print(f"DEBUG: Skipping empty simplification for axiom {axiom_id}")
                        continue
                    
                    print(f"DEBUG: Found simplification: {axiom_id} -> {original} -> {simplified}")
                    simplifications[axiom_id] = simplified
                else:
                    print(f"DEBUG: No match for line: {repr(line)}")
        
        return axioms_used, simplifications, steps
    
    def analyze_step_correctness(self, step: DerivationStep, all_axioms: Dict[int, Axiom], all_steps: List[DerivationStep] = None) -> StepCorrectness:
        """Check if a derivation step is correct."""
        if all_steps is None:
            all_steps = []
            
        # Convert premise references to actual axioms
        premise_axioms = []
        
        # New standard: Check that all premises are either provided axioms or results of previous steps
        current_step_index = None
        for i, s in enumerate(all_steps):
            if s.step_id == step.step_id:
                current_step_index = i
                break
        
        for premise in step.premises:
            # Check if it's a digit or a digit in parentheses like (1), (2), etc.
            if premise.isdigit() or (premise.startswith("(") and premise.endswith(")") and premise[1:-1].isdigit()):
                # It's an axiom index - this is valid as it refers to provided axioms
                # Extract the index, removing parentheses if present
                idx = int(premise) if premise.isdigit() else int(premise[1:-1])
                if 0 <= idx < len(all_axioms):
                    premise_axioms.append(all_axioms[idx].original)
                else:
                    print(f"WARNING: Axiom index {idx} is out of range (0-{len(all_axioms)-1})")
                    return StepCorrectness.INCORRECT
            elif premise.startswith("STEP"):
                # Find the referenced step and use its conclusion
                # Add recursion protection
                referenced_conclusion = self.resolve_step_reference(premise, all_steps, max_depth=5)
                if referenced_conclusion:
                    premise_axioms.append(referenced_conclusion)
                else:
                    print(f"WARNING: Could not resolve step reference {premise} due to recursion limit")
                    return StepCorrectness.INCORRECT
            else:
                # It's already an axiom string - check if it matches any provided axiom
                axiom_found = False
                for axiom in all_axioms.values():
                    if axiom.original == premise or axiom.simplified == premise:
                        premise_axioms.append(premise)
                        axiom_found = True
                        break
                
                if not axiom_found:
                    # Check if it matches any previous step conclusion
                    step_conclusion_found = False
                    if current_step_index is not None:
                        for i in range(current_step_index):
                            if all_steps[i].conclusion == premise:
                                premise_axioms.append(premise)
                                step_conclusion_found = True
                                break
                    
                    if not step_conclusion_found:
                        print(f"WARNING: Premise '{premise}' is neither a provided axiom nor a result of previous steps")
                        return StepCorrectness.INCORRECT
        
        # Prepare all axioms (as strings) - use all axioms from the prompt, not just selected ones
        all_axioms_list = [ax.original for ax in all_axioms.values()]
        reasoner = DeepOntoDLReasoner()
        
        # Debug: print what we're checking
        # print(f"DEBUG: Checking step {step.step_id}")
        # print(f"DEBUG: Premises: {premise_axioms}")
        # print(f"DEBUG: Conclusion: {step.conclusion}")
        
        # Check if conclusion follows from premises
        totally = reasoner.check_subsumption(premise_axioms, step.conclusion)
        # print(f"DEBUG: Totally correct check result: {totally}")
        if totally:
            return StepCorrectness.TOTALLY_CORRECT
        
        # Check if conclusion follows from all axioms
        partially = reasoner.check_subsumption(all_axioms_list, step.conclusion)
        # print(f"DEBUG: Partially correct check result: {partially}")
        if partially:
            return StepCorrectness.PARTIALLY_CORRECT
        
        return StepCorrectness.INCORRECT
    
    def resolve_step_reference(self, step_id: str, all_steps: List[DerivationStep], max_depth: int = 5, current_depth: int = 0) -> str:
        """Resolve a step reference to its conclusion, with recursion protection."""
        if current_depth >= max_depth:
            print(f"WARNING: Maximum recursion depth ({max_depth}) reached for step {step_id}")
            return None
        
        # Find the step
        for step in all_steps:
            if step.step_id == step_id:
                # Check if this step has any step references in its premises
                has_step_refs = any(p.startswith('STEP') for p in step.premises)
                
                if has_step_refs:
                    # This step depends on other steps, resolve them first
                    resolved_premises = []
                    for premise in step.premises:
                        if premise.startswith('STEP'):
                            resolved = self.resolve_step_reference(premise, all_steps, max_depth, current_depth + 1)
                            if resolved:
                                resolved_premises.append(resolved)
                            else:
                                return None  # Cannot resolve dependency
                        else:
                            # Direct axiom reference, keep as is
                            resolved_premises.append(premise)
                    
                    return step.conclusion
                else:
                    return step.conclusion
        
        return None
    
    def check_simplification_correctness(self, original_axiom: str, simplified_axiom: str) -> bool:
        """Check if a simplification is correct: first try simple form check, only use reasoner if needed."""
        # 1. Simple form check
        if original_axiom == simplified_axiom:
            return True
        
        # Try simple subclass/equivalence form check
        import re
        def parse_axiom(axiom):
            # Returns (type, left, right) or None
            axiom = axiom.strip()
            if '≡' in axiom:
                parts = axiom.split('≡', 1)
                return ('equiv', parts[0].strip(), parts[1].strip())
            if '⊑' in axiom:
                parts = axiom.split('⊑', 1)
                return ('sub', parts[0].strip(), parts[1].strip())
            return None
        
        orig = parse_axiom(original_axiom)
        simp = parse_axiom(simplified_axiom)
        
        # If both are subclass axioms and identical sides
        if orig and simp and orig[0] == simp[0]:
            if orig[1] == simp[1] and orig[2] == simp[2]:
                return True
        
        # Check equivalence to subsumption simplification
        if orig and orig[0] == 'equiv' and simp and simp[0] == 'sub':
            # Case 1: A ≡ B becomes B ⊑ A (right side becomes left side)
            if orig[2] == simp[1] and orig[1] == simp[2]:
                return True
            # Case 2: A ≡ B ⊓ C ⊓ D becomes A ⊑ B, A ⊑ C, A ⊑ D (decomposition)
            if orig[1] == simp[1]:  # Left side is the same
                # Check if simplified is one of the conjuncts from the right side
                right_side = orig[2]
                # Split by intersection (⊓) at top level
                def split_intersection(expr):
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
                        elif c == '⊓' and paren == 0:
                            parts.append(current.strip())
                            current = ''
                            i += 1
                            continue
                        current += c
                        i += 1
                    if current:
                        parts.append(current.strip())
                    return parts
                
                conjuncts = split_intersection(right_side)
                if simp[2] in conjuncts:
                    return True
        
        # Check subsumption to subsumption decomposition
        if orig and orig[0] == 'sub' and simp and simp[0] == 'sub':
            # Case: A ⊑ B ⊓ C ⊓ D becomes A ⊑ B, A ⊑ C, A ⊑ D (decomposition)
            if orig[1] == simp[1]:  # Left side is the same
                # Check if simplified is one of the conjuncts from the right side
                right_side = orig[2]
                # Split by intersection (⊓) at top level
                def split_intersection(expr):
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
                        elif c == '⊓' and paren == 0:
                            parts.append(current.strip())
                            current = ''
                            i += 1
                            continue
                        current += c
                        i += 1
                    if current:
                        parts.append(current.strip())
                    return parts
                
                conjuncts = split_intersection(right_side)
                if simp[2] in conjuncts:
                    return True
        
        # 2. If simple check fails, use reasoner
        reasoner = DeepOntoDLReasoner()
        is_correct = reasoner.check_subsumption([original_axiom], simplified_axiom)
        return is_correct
    
    def calculate_axiom_weight(self, axiom: str) -> int:
        """Calculate the weight of an axiom based on its logical operators and symbols."""
        weight = 0
        
        # Count equivalence (≡) - weight 2
        weight += axiom.count("≡") * 2
        
        # Count other logical operators and symbols - weight 1 each
        symbols = ["⊑", "⊓", "⊔", "∃", "∀", "¬", "⊤", "⊥"]
        for symbol in symbols:
            weight += axiom.count(symbol)
        
        # Count concept names (A followed by digits)
        import re
        concept_matches = re.findall(r'A\d+', axiom)
        weight += len(concept_matches)
        
        # Count role names (r followed by digits)
        role_matches = re.findall(r'r\d+', axiom)
        weight += len(role_matches)
        
        return weight
 
    
    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a single JSON file."""
        print(f"Analyzing file: {file_path}")
        print("=" * 50)
        
        # Load the JSON file
        data = self.load_json_file(file_path)
        
        # Extract axioms from prompt
        self.axioms = self.extract_axioms_from_prompt(data['prompt'])
        
        # Check if any axiom contains ObjectPropertyDomain, SubObjectPropertyOf, ObjectComplementOf, or ObjectUnionOf
        for axiom_id, axiom in self.axioms.items():
            if ("ObjectPropertyDomain" in axiom.original or 
                "SubObjectPropertyOf" in axiom.original or 
                "ObjectComplementOf" in axiom.original or 
                "ObjectUnionOf" in axiom.original):
                print(f"Skipping sample - found axiom containing ObjectPropertyDomain, SubObjectPropertyOf, ObjectComplementOf, or ObjectUnionOf:")
                print(f"  Axiom {axiom_id}: {axiom.original}")
                return {
                    'file': file_path,
                    'axioms': self.axioms,
                    'target_conclusion': "",
                    'steps': [],
                    'analysis': 'Skipped - contains ObjectPropertyDomain, SubObjectPropertyOf, ObjectComplementOf, or ObjectUnionOf'
                }
        
        print(f"Found {len(self.axioms)} axioms:")
        for axiom_id, axiom in self.axioms.items():
            print(f"  Axiom {axiom_id}: {axiom.original}")
        
        # Extract target conclusion
        self.target_conclusion = self.extract_target_conclusion(data['prompt'])
        print(f"\nTarget conclusion: {self.target_conclusion}")
        
        # Extract reasoning-dsl from response
        dsl_text = self.extract_reasoning_dsl(data['response'])
        if not dsl_text:
            print("\nNo reasoning-dsl found in response!")
            return {
                'file': file_path,
                'axioms': self.axioms,
                'target_conclusion': self.target_conclusion,
                'steps': [],
                'analysis': 'No reasoning-dsl found'
            }
        
        print(f"\nFound reasoning-dsl:")
        print(dsl_text)
        
        # Parse the reasoning-dsl
        axioms_used, simplifications, steps = self.parse_reasoning_dsl(dsl_text)
        
        print(f"\nParsed analysis:")
        print(f"Axioms used: {axioms_used}")
        print(f"Simplifications: {simplifications}")
        print(f"Steps: {len(steps)}")
        # input("press Enter to continue...")
        
        # Check simplification correctness
        print(f"\nChecking simplifications:")
        simplification_results = {}
        total_simplified_weight = 0
        total_original_weight = 0
        
        for axiom_id, simplified_text in simplifications.items():
            if axiom_id.startswith("(") and axiom_id.endswith(")"):
                axiom_id = axiom_id[1:-1]
            
            # print(axiom_id, simplified_text)
            # input("press Enter to continue...")

            if int(axiom_id) in self.axioms:
                original_text = self.axioms[int(axiom_id)].original # Convert string key to int for lookup
                if "," in simplified_text:
                    simplified_axiom_list = [a.strip() for a in simplified_text.split(",")]
                elif "and" in simplified_text:
                    simplified_axiom_list = [a.strip() for a in simplified_text.split("and")]
                else:
                    simplified_axiom_list = [simplified_text.strip()]
                
                for simplified_axiom in simplified_axiom_list:
                    is_correct = self.check_simplification_correctness(original_text, simplified_axiom)
                    if not is_correct:
                        break
                simplification_results[axiom_id] = is_correct
                
                total_original_weight += self.calculate_axiom_weight(original_text)
                total_simplified_weight += self.calculate_axiom_weight(simplified_text)
                
                status = "✓" if is_correct else "✗"
                print(f"  Axiom {axiom_id}: {status} {original_text} -> {simplified_text}")
                # print(f"    Weight reduction: {weight_dropped} ({percentage_dropped:.1f}%)")
            else:
                print(f"  Axiom {axiom_id}: [NOT FOUND IN PROMPT] -> {simplified_text}")
        
        total_weight_dropped = total_original_weight - total_simplified_weight
        
        
        # Analyze each step
        print(f"\nChecking derivation steps:")
        step_conclusions = {}  # Map step_id to conclusion
        
        for step in steps:
            # Create a mapping of step references to their conclusions
            step_conclusions[step.step_id] = step.conclusion
            
            # Modify the step premises to replace STEP references with actual conclusions
            resolved_premises = []
            for premise in step.premises:
                if premise.startswith("STEP"):
                    # Find the referenced step and use its conclusion
                    step_number = premise  # e.g., "STEP1", "STEP2"
                    referenced_step = None
                    for s in steps: # Changed 'all_steps' to 'steps' to avoid confusion
                        if s.step_id == step_number:
                            referenced_step = s
                            break
                    
                    if referenced_step:
                        # Use the conclusion of the referenced step as a premise
                        resolved_premises.append(referenced_step.conclusion)
                    else:
                        # If step not found, add the original reference (will be treated as invalid)
                        resolved_premises.append(premise)
                else:
                    resolved_premises.append(premise)
            
            # Create a temporary step with resolved premises for analysis
            temp_step = DerivationStep(
                step_id=step.step_id,
                premises=resolved_premises,
                conclusion=step.conclusion,
                explanation=step.explanation,
                correctness=StepCorrectness.INCORRECT
            )
            
            step.correctness = self.analyze_step_correctness(temp_step, self.axioms, steps)
            status_icon = "✓" if step.correctness == StepCorrectness.TOTALLY_CORRECT else "?" if step.correctness == StepCorrectness.PARTIALLY_CORRECT else "✗"
            print(f"\n{step.step_id}: {status_icon}")
            print(f"  Premises: {step.premises}")
            print(f"  Conclusion: {step.conclusion}")
            print(f"  Explanation: {step.explanation}")
            print(f"  Correctness: {step.correctness.value}")
        
        
        # Generate summary
        print("\n==================================================")
        print("SUMMARY")
        print("==================================================")
        
        # Calculate individual simplification correctness
        num_correct_simplifications = sum(simplification_results.values())
        total_simplifications = len(simplification_results) if simplification_results else 0
        individual_accuracy = (num_correct_simplifications / total_simplifications * 100) if total_simplifications > 0 else -1

        if 'correct_ids' in data and axioms_used is not None:
            correct_ids_set = set(data['correct_ids'])
            axioms_used_set = set(axioms_used)
            jaccard_similarity = self.calculate_jaccard_similarity(correct_ids_set, axioms_used_set)
            print(f"\n=====Jaccard Similarity between correct_ids and AXIOMS_USED: {jaccard_similarity:.4f}======")
            print(f"  correct_ids: {data['correct_ids']}")
            print(f"  AXIOMS_USED: {axioms_used}")
            # print(f"  Intersection: {list(correct_ids_set.intersection(axioms_used_set))}")
            # print(f"  Union: {list(correct_ids_set.union(axioms_used_set))}")

        
        print(f"=====Simplifications (SIMPLIFY)=====")
        print(f"  Axiom-wise Accuracy: {individual_accuracy:.2f}% ({num_correct_simplifications}/{total_simplifications} correct)")
        
        # Check if simplified axioms can derive the target conclusion
        can_derive_conclusion = False
        if simplifications and self.target_conclusion:
            can_derive_conclusion = self.check_simplified_axioms_inference(simplifications, self.target_conclusion)
            print(f"  Overall-Correctness: {'✓' if can_derive_conclusion else '✗'}")
        
        # Add weight reduction summary
        if total_original_weight > 0:
            total_percentage_dropped = (total_weight_dropped / total_original_weight * 100)
            print(f"  length dropped: {total_weight_dropped} units ({total_percentage_dropped:.1f}%, from {total_original_weight} units to {total_original_weight - total_weight_dropped} units\n")
        
        print("=====Derivation steps (DERIVE):=====")
        step_correctness_counts = {
            StepCorrectness.TOTALLY_CORRECT: 0,
            StepCorrectness.PARTIALLY_CORRECT: 0,
            StepCorrectness.INCORRECT: 0
        }
        for step in steps:
            step_correctness_counts[step.correctness] += 1
        
        # Display number of derivation steps
        total_steps = len(steps)
        if total_steps > 0:
            correct_steps = step_correctness_counts[StepCorrectness.TOTALLY_CORRECT]
            accuracy = (correct_steps / total_steps) * 100
            print(f"  Step-wise accuracy: {accuracy:.1f}% ({correct_steps}/{total_steps} steps)")
        
        # Check if target conclusion is reached
        if steps:
            final_step = steps[-1]
            # Normalize whitespace for comparison
            normalized_final = final_step.conclusion.replace(' ', '')
            normalized_target = self.target_conclusion.replace(' ', '')
            target_reached = normalized_final == normalized_target
        else:
            target_reached = None
                
        
        # Calculate explanation_correctness: true iff every step is correct and the desired target is reached
        explanation_correctness = False
        if steps and target_reached is not None:
            all_steps_correct = all(step.correctness == StepCorrectness.TOTALLY_CORRECT for step in steps)
            explanation_correctness = all_steps_correct and target_reached
            print(f"  Explanation Overall Correctness: {'✓' if explanation_correctness else '✗'}")
        
        result = {
            'file': file_path,
            'axioms': self.axioms,
            'target_conclusion': self.target_conclusion,
            'target_reached': target_reached,
            'explanation_correctness': explanation_correctness,
            'num_derivation_steps': len(steps),
            'steps': steps,
            'simplifications': simplification_results,
            'individual_simplification_accuracy': individual_accuracy,
            'simplified_axioms_can_derive': can_derive_conclusion,
            'weight_stats': {
                'total_dropped': total_weight_dropped,
                'total_original': total_original_weight
            },
            'analysis': 'Analysis completed'
        }
        
        # Add Jaccard similarity to the result if correct_ids are available
        if 'correct_ids' in data and axioms_used is not None:
            correct_ids_set = set(data['correct_ids'])
            axioms_used_set = set(axioms_used)
            jaccard_similarity = self.calculate_jaccard_similarity(correct_ids_set, axioms_used_set)
            result['jaccard_similarity'] = {
                'score': jaccard_similarity,
                'correct_ids': list(correct_ids_set),
                'axioms_used': list(axioms_used_set),
                'intersection': list(correct_ids_set.intersection(axioms_used_set)),
                'union': list(correct_ids_set.union(axioms_used_set))
            }
            
        return result

def main():
    if len(sys.argv) != 2:
        print("Usage: python analysis_script.py <json_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    analyzer = ReasoningAnalyzer()
    
    try:
        result = analyzer.analyze_file(file_path)
        print(f"\nAnalysis completed for {file_path}")
    except Exception as e:
        print(f"Error analyzing file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 