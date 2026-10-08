"""Small fictional extraction regression set, independent of classifier scores."""
import argparse
import asyncio
import json
from pathlib import Path
from agents.extractor import ExtractorAgent
from agents.llm_provider import create_provider
import config

async def evaluate(cases):
    provider = create_provider(provider_type=config.LLM_PROVIDER,
        model=getattr(config, f'{config.LLM_PROVIDER.upper()}_MODEL_EXTRACT'),
        api_key=getattr(config, f'{config.LLM_PROVIDER.upper()}_API_KEY', ''),
        base_url=config.OLLAMA_BASE_URL)
    agent = ExtractorAgent(provider)
    results = []
    for case in cases:
        result = await agent.extract(case['conversation'])
        actual = result['bayes_features']
        mismatches = {k: {'expected': v, 'actual': actual.get(k, 'unknown')}
                      for k, v in case['expected'].items() if actual.get(k, 'unknown') != v}
        results.append({'id': case['id'], 'checked_features': len(case['expected']),
                        'extraction_returned_data': bool(result.get('raw_extracted')), 'mismatches': mismatches})
    return {'provider': config.LLM_PROVIDER, 'model': getattr(config, f'{config.LLM_PROVIDER.upper()}_MODEL_EXTRACT'),
            'scope': 'Small fictional regression set; not clinical or classifier evaluation', 'cases': results}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calls the configured provider with fictional cases')
    parser.add_argument('--cases', type=Path, default=Path(__file__).parent / 'examples/extraction_cases.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(asyncio.run(evaluate(json.loads(args.cases.read_text()))), indent=2))
