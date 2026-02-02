#!/usr/bin/env python3
"""
Extract and analyze knowledge from 9 knowledge base markdown files.
Creates a comprehensive analysis for project applicability.
"""

import re
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

class KnowledgeExtractor:
    def __init__(self, kb_files: List[str]):
        self.kb_files = kb_files
        self.knowledge = {}

    def extract_metadata(self, content: str) -> Dict:
        """Extract YAML frontmatter metadata"""
        metadata = {}
        yaml_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
        if yaml_match:
            yaml_content = yaml_match.group(1)
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"')
        return metadata

    def extract_transcription(self, content: str) -> str:
        """Extract full transcription text (no images)"""
        # Find transcription section
        trans_start = content.find('## 🎬 Transcripción Completa')
        if trans_start == -1:
            return ""

        # Extract text, skip image markers
        lines = []
        for line in content[trans_start:].split('\n'):
            # Skip image lines (base64 or ![...])
            if line.strip().startswith('![') or 'data:image' in line:
                continue
            # Skip markdown image syntax
            if re.match(r'^\s*<a id=', line):
                continue
            lines.append(line)

        return '\n'.join(lines)

    def extract_tools(self, text: str) -> List[str]:
        """Extract mentioned tools and technologies"""
        tools = set()

        # Common tool patterns
        patterns = [
            r'\b(Next\.js|React|Vue|Angular|Svelte)\b',
            r'\b(TypeScript|JavaScript|Python|Rust|Go)\b',
            r'\b(Prisma|Drizzle|Supabase|Firebase)\b',
            r'\b(AWS|Azure|Google Cloud|Vercel|Netlify)\b',
            r'\b(Stripe|PayPal|Cognito|Auth0)\b',
            r'\b(Claude|GPT-4|ChatGPT|Anthropic|OpenAI)\b',
            r'\b(Docker|Kubernetes|Terraform)\b',
            r'\b(GitHub|GitLab|Bitbucket)\b',
            r'\b(Tailwind|shadcn/ui|Material-UI|Chakra)\b',
            r'\b(Astro|Sanity|DynamoDB|PostgreSQL|MongoDB)\b'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tools.update(matches)

        return sorted(list(tools))

    def extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts and topics"""
        concepts = []

        # Look for numbered lists, bullet points, and bold text
        # Numbered items
        numbered = re.findall(r'^\d+\.\s+\*\*(.*?)\*\*', text, re.MULTILINE)
        concepts.extend(numbered)

        # Bold concepts
        bold = re.findall(r'\*\*(.*?)\*\*', text)
        concepts.extend([b for b in bold if len(b) < 100])  # Filter long text

        # Headers
        headers = re.findall(r'^#{2,4}\s+(.+)$', text, re.MULTILINE)
        concepts.extend(headers)

        # Deduplicate and clean
        unique = list(set([c.strip() for c in concepts if len(c.strip()) > 5]))
        return sorted(unique)[:50]  # Top 50 concepts

    def extract_code_blocks(self, text: str) -> List[str]:
        """Extract code examples"""
        code_blocks = re.findall(r'```(\w+)?\n(.*?)\n```', text, re.DOTALL)
        return [{'language': lang or 'unknown', 'code': code.strip()}
                for lang, code in code_blocks]

    def extract_timestamps_topics(self, text: str) -> List[Tuple[str, str]]:
        """Extract timestamp -> topic mapping from index"""
        timestamps = []
        # Pattern: - [HH:MM:SS](#tsXXX) - Topic text
        pattern = r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\(#ts\d+\)\s*-\s*(.+?)(?:\.\.\.|$)'
        matches = re.findall(pattern, text)
        return [(ts, topic.strip()) for ts, topic in matches]

    def extract_metrics(self, text: str) -> Dict[str, str]:
        """Extract quantified metrics (ROI, time savings, costs)"""
        metrics = {}

        # Look for percentages
        pct_pattern = r'(\d+%)\s+(\w+(?:\s+\w+){0,5})'
        for match in re.finditer(pct_pattern, text):
            metrics[match.group(2)] = match.group(1)

        # Look for time savings (e.g., "2 hours -> 20 minutes")
        time_pattern = r'(\d+)\s*(hours?|minutes?|mins?|h|min)\s*→\s*(\d+)\s*(hours?|minutes?|mins?|h|min)'
        for match in re.finditer(time_pattern, text, re.IGNORECASE):
            key = f"Time reduction ({match.group(2)} to {match.group(4)})"
            value = f"{match.group(1)} → {match.group(3)}"
            metrics[key] = value

        # Look for costs
        cost_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*/?\s*(\w+)?'
        costs = re.findall(cost_pattern, text)
        if costs:
            metrics['Costs mentioned'] = ', '.join([f"${c[0]}" for c in costs[:5]])

        return metrics

    def analyze_file(self, filepath: str) -> Dict:
        """Analyze a single knowledge base file"""
        print(f"\n📖 Analyzing: {Path(filepath).name}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")
            return {}

        # Extract components
        metadata = self.extract_metadata(content)
        transcription = self.extract_transcription(content)

        analysis = {
            'filename': Path(filepath).name,
            'metadata': metadata,
            'duration': metadata.get('duration', 'Unknown'),
            'frames': metadata.get('frames_extracted', 'Unknown'),
            'tools': self.extract_tools(transcription),
            'concepts': self.extract_key_concepts(transcription),
            'code_examples': len(self.extract_code_blocks(transcription)),
            'timeline': self.extract_timestamps_topics(content),
            'metrics': self.extract_metrics(transcription),
            'word_count': len(transcription.split()),
            'summary': metadata.get('title', '').replace('ssVid.net--', '')
        }

        print(f"  ✅ Duration: {analysis['duration']}")
        print(f"  ✅ Frames: {analysis['frames']}")
        print(f"  ✅ Tools found: {len(analysis['tools'])}")
        print(f"  ✅ Concepts: {len(analysis['concepts'])}")
        print(f"  ✅ Timeline entries: {len(analysis['timeline'])}")
        print(f"  ✅ Word count: {analysis['word_count']:,}")

        return analysis

    def cross_analyze(self) -> Dict:
        """Find patterns across all knowledge bases"""
        all_tools = defaultdict(int)
        all_concepts = defaultdict(int)
        all_metrics = {}

        for kb_name, kb_data in self.knowledge.items():
            # Count tool mentions
            for tool in kb_data.get('tools', []):
                all_tools[tool] += 1

            # Count concept mentions
            for concept in kb_data.get('concepts', []):
                all_concepts[concept] += 1

            # Aggregate metrics
            for metric, value in kb_data.get('metrics', {}).items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append((kb_name, value))

        return {
            'most_common_tools': sorted(all_tools.items(), key=lambda x: x[1], reverse=True)[:20],
            'most_common_concepts': sorted(all_concepts.items(), key=lambda x: x[1], reverse=True)[:30],
            'metrics_summary': all_metrics
        }

    def generate_report(self, output_file: str):
        """Generate comprehensive markdown report"""
        print(f"\n📝 Generating report: {output_file}")

        cross = self.cross_analyze()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 📊 COMPREHENSIVE KNOWLEDGE BASE ANALYSIS\n\n")
            f.write(f"**Generated**: 2025-11-22\n")
            f.write(f"**Files Analyzed**: {len(self.knowledge)}\n\n")

            # Executive summary
            f.write("## 🎯 Executive Summary\n\n")
            total_duration = sum([int(kb.get('metadata', {}).get('duration', '0:0').split(':')[0]) * 60 +
                                 int(kb.get('metadata', {}).get('duration', '0:0').split(':')[1])
                                 for kb in self.knowledge.values()
                                 if 'duration' in kb.get('metadata', {})])
            f.write(f"- **Total Duration**: {total_duration // 60}h {total_duration % 60}min\n")
            f.write(f"- **Total Word Count**: {sum([kb.get('word_count', 0) for kb in self.knowledge.values()]):,}\n")
            f.write(f"- **Unique Tools Identified**: {len(cross['most_common_tools'])}\n")
            f.write(f"- **Key Concepts Extracted**: {len(cross['most_common_concepts'])}\n\n")

            # Most common tools
            f.write("## 🛠️ Most Mentioned Tools & Technologies\n\n")
            for tool, count in cross['most_common_tools']:
                f.write(f"- **{tool}**: mentioned in {count} KB(s)\n")
            f.write("\n")

            # Top concepts
            f.write("## 💡 Top Concepts Across All KBs\n\n")
            for concept, count in cross['most_common_concepts'][:20]:
                f.write(f"- {concept} ({count}x)\n")
            f.write("\n")

            # Individual KB summaries
            f.write("## 📚 Individual Knowledge Base Summaries\n\n")
            for kb_name, kb_data in sorted(self.knowledge.items()):
                f.write(f"### {kb_data['summary']}\n\n")
                f.write(f"- **Duration**: {kb_data['duration']}\n")
                f.write(f"- **Frames**: {kb_data['frames']}\n")
                f.write(f"- **Word Count**: {kb_data['word_count']:,}\n")
                f.write(f"- **Code Examples**: {kb_data['code_examples']}\n\n")

                if kb_data.get('tools'):
                    f.write(f"**Tools**: {', '.join(kb_data['tools'][:10])}\n\n")

                if kb_data.get('timeline'):
                    f.write(f"**Key Topics** (first 10):\n")
                    for ts, topic in kb_data['timeline'][:10]:
                        f.write(f"- [{ts}] {topic}\n")
                    f.write("\n")

                if kb_data.get('metrics'):
                    f.write(f"**Metrics Mentioned**:\n")
                    for metric, value in list(kb_data['metrics'].items())[:5]:
                        f.write(f"- {metric}: {value}\n")
                    f.write("\n")

                f.write("---\n\n")

            # Project recommendations
            f.write("## 🎯 Recommendations by Project\n\n")
            f.write(self._generate_project_recommendations())

        print(f"✅ Report generated: {output_file}")

    def _generate_project_recommendations(self) -> str:
        """Generate recommendations based on analyzed knowledge bases."""
        recs = """
### General Recommendations

Based on the analyzed knowledge bases, here are actionable recommendations:

1. **Identify common tools** across knowledge bases for technology consolidation
2. **Extract code patterns** that appear in multiple sources
3. **Build a unified knowledge base** from the most frequently mentioned concepts
4. **Prioritize high-impact topics** that appear across multiple sources
"""
        return recs

    def run(self, output_report: str):
        """Main execution"""
        print("=" * 60)
        print("🚀 KNOWLEDGE BASE EXTRACTION STARTING")
        print("=" * 60)

        # Analyze each file
        for filepath in self.kb_files:
            kb_name = Path(filepath).stem
            self.knowledge[kb_name] = self.analyze_file(filepath)

        # Cross-analysis
        print("\n" + "=" * 60)
        print("🔍 CROSS-ANALYSIS")
        print("=" * 60)

        cross = self.cross_analyze()
        print(f"\n✅ Found {len(cross['most_common_tools'])} unique tools")
        print(f"✅ Found {len(cross['most_common_concepts'])} unique concepts")

        # Generate report
        print("\n" + "=" * 60)
        print("📊 GENERATING REPORT")
        print("=" * 60)

        self.generate_report(output_report)

        print("\n" + "=" * 60)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract and analyze knowledge from .knowledge.md files"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Knowledge base .md files to analyze",
    )
    parser.add_argument(
        "-o", "--output",
        default="knowledge_analysis.md",
        help="Output report path (default: knowledge_analysis.md)",
    )
    args = parser.parse_args()

    extractor = KnowledgeExtractor(args.files)
    extractor.run(args.output)

    print(f"\nFull report available at:\n{args.output}")
