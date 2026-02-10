# Bank Skill

AI agents can check balances, send money, and share account details via the [Wise API](https://wise.com).

## Installation

### Via npm
```bash
npm install -g @singularityhacker/bank-skill
```

### Via skills.sh
```bash
npx skills add singularityhacker/bank-skills
```

### Via GitHub
```bash
npx skills add github:singularityhacker/bank-skills
```

## Quick Start

1. Get a Wise Business account and API token
2. Set environment variable:
   ```bash
   export WISE_API_TOKEN='your-token-here'
   ```
3. Use the skill:
   ```bash
   echo '{"action": "balance"}' | bank-skill
   ```

## Features

- **Check balances** — Query multi-currency Wise balances
- **Send money** — Initiate USD ACH or EUR IBAN transfers
- **Share receive details** — Get account/routing numbers for receiving payments

## Documentation

Full documentation: https://github.com/singularityhacker/bank-skills

## Links

- **npm**: https://www.npmjs.com/package/@singularityhacker/bank-skill
- **GitHub**: https://github.com/singularityhacker/bank-skills
- **skills.sh**: https://skills.sh/ (search for "bank-skill")

## License

MIT
