# CodeBased MVP Implementation Strategy

## Simplified Architecture (No LSP)

```typescript
// Main entry point for CLI
interface CodeBasedConfig {
  projectRoot: string;
  outputPath: string;
  targets: {
    angular: boolean;
    nodejs: boolean;
  };
  ignorePatterns?: string[];
  monorepo?: {
    type: 'nx' | 'lerna' | 'yarn-workspaces' | 'npm-workspaces';
    packages?: string[]; // Optional explicit package paths
  };
}

export class CodeBasedCLI {
  async generateGraph(config: CodeBasedConfig): Promise<void> {
    console.log('🔍 Analyzing codebase...');
    
    // Phase 1: Build file/folder hierarchy
    const hierarchyBuilder = new HierarchyBuilder(config);
    const fileGraph = await hierarchyBuilder.build();
    
    // Phase 2: Parse code structures
    const codeParser = new CodeStructureParser(config);
    const codeGraph = await codeParser.parse(fileGraph);
    
    // Phase 3: Detect relationships (no LSP needed)
    const relationshipDetector = new RelationshipDetector(config);
    const completeGraph = await relationshipDetector.analyze(codeGraph);
    
    // Phase 4: Output to Kuzu format
    const kuzuExporter = new KuzuExporter(config.outputPath);
    await kuzuExporter.export(completeGraph);
    
    console.log('✅ Graph generated successfully!');
  }
  
  async updateGraph(config: CodeBasedConfig, changedFiles: string[]): Promise<void> {
    console.log(`🔄 Updating graph for ${changedFiles.length} changed files...`);
    
    // Incremental update logic
    const updater = new IncrementalUpdater(config);
    await updater.updateFiles(changedFiles);
    
    console.log('✅ Graph updated successfully!');
  }
}
```

## Simplified Parsing Strategy (MVP)

```typescript
class CodeStructureParser {
  private parsers: Map<string, LanguageParser>;
  
  constructor(config: CodeBasedConfig) {
    this.parsers = new Map();
    
    if (config.targets.nodejs || config.targets.angular) {
      this.parsers.set('.ts', new TypeScriptParser());
      this.parsers.set('.js', new JavaScriptParser());
      this.parsers.set('.tsx', new TypeScriptParser({ jsx: true }));
      this.parsers.set('.jsx', new JavaScriptParser({ jsx: true }));
    }
    
    if (config.targets.angular) {
      this.parsers.set('.html', new AngularTemplateParser());
    }
  }
  
  async parse(fileGraph: Graph): Promise<Graph> {
    const files = fileGraph.getNodesByType('FILE');
    
    // Process files in parallel
    const batchSize = 50;
    for (let i = 0; i < files.length; i += batchSize) {
      const batch = files.slice(i, i + batchSize);
      await Promise.all(batch.map(file => this.parseFile(file, fileGraph)));
    }
    
    return fileGraph;
  }
  
  private async parseFile(fileNode: Node, graph: Graph): Promise<void> {
    const ext = path.extname(fileNode.metadata.path);
    const parser = this.parsers.get(ext);
    
    if (!parser) return;
    
    try {
      const content = await fs.readFile(fileNode.metadata.path, 'utf-8');
      await parser.parse(content, fileNode, graph);
    } catch (error) {
      // Create error node but continue parsing
      this.handleParseError(error, fileNode, graph);
    }
  }
}
```

## TypeScript/JavaScript Parser (Simplified for MVP)

```typescript
class TypeScriptParser implements LanguageParser {
  private parser: Parser;
  
  constructor(options: { jsx?: boolean } = {}) {
    this.parser = new Parser();
    const lang = options.jsx 
      ? require('tree-sitter-typescript').tsx
      : require('tree-sitter-typescript').typescript;
    this.parser.setLanguage(lang);
  }
  
  async parse(content: string, fileNode: Node, graph: Graph): Promise<void> {
    const tree = this.parser.parse(content);
    const visitor = new TypeScriptVisitor(fileNode, graph, content);
    visitor.visit(tree.rootNode);
  }
}

class TypeScriptVisitor {
  // Simplified node types for MVP
  private readonly nodeHandlers = new Map([
    ['class_declaration', this.handleClass.bind(this)],
    ['function_declaration', this.handleFunction.bind(this)],
    ['interface_declaration', this.handleInterface.bind(this)],
    ['import_statement', this.handleImport.bind(this)],
    ['export_statement', this.handleExport.bind(this)],
    ['variable_statement', this.handleVariable.bind(this)]
  ]);
  
  constructor(
    private fileNode: Node,
    private graph: Graph,
    private sourceCode: string
  ) {}
  
  visit(node: any): void {
    const handler = this.nodeHandlers.get(node.type);
    if (handler) {
      handler(node);
    }
    
    // Visit children
    for (let i = 0; i < node.childCount; i++) {
      this.visit(node.child(i));
    }
  }
  
  private handleClass(node: any): void {
    const className = this.getNodeName(node);
    const decorators = this.extractDecorators(node);
    
    // Determine if this is an Angular construct
    let nodeType = 'CLASS';
    if (decorators.includes('Component')) {
      nodeType = decorators.includes('standalone: true') 
        ? 'STANDALONE_COMPONENT' 
        : 'COMPONENT';
    } else if (decorators.includes('Injectable')) {
      nodeType = 'SERVICE';
    } else if (decorators.includes('Directive')) {
      nodeType = 'DIRECTIVE';
    } else if (decorators.includes('Pipe')) {
      nodeType = 'PIPE';
    } else if (decorators.includes('NgModule')) {
      nodeType = 'MODULE';
    }
    
    const classNode: Node = {
      id: `${this.fileNode.id}#${className}`,
      type: nodeType,
      name: className,
      metadata: {
        path: this.fileNode.metadata.path,
        start_line: node.startPosition.row + 1,
        end_line: node.endPosition.row + 1,
        decorators,
        // For AI context, include a snippet
        snippet: this.extractSnippet(node)
      }
    };
    
    this.graph.addNode(classNode);
    this.graph.addEdge({
      source_id: this.fileNode.id,
      target_id: classNode.id,
      type: 'DEFINES',
      metadata: {}
    });
    
    // Handle Angular-specific metadata
    if (nodeType === 'COMPONENT' || nodeType === 'STANDALONE_COMPONENT') {
      this.handleComponentMetadata(classNode, node);
    }
  }
  
  private handleImport(node: any): void {
    const importPath = this.extractImportPath(node);
    const specifiers = this.extractImportSpecifiers(node);
    
    // For MVP, just track external package imports
    if (this.isExternalPackage(importPath)) {
      const packageName = this.getPackageName(importPath);
      
      // Create or get package reference node
      const packageId = `package:${packageName}`;
      if (!this.graph.hasNode(packageId)) {
        this.graph.addNode({
          id: packageId,
          type: 'EXTERNAL_PACKAGE',
          name: packageName,
          metadata: { external: true }
        });
      }
      
      // Create import edge
      this.graph.addEdge({
        source_id: this.fileNode.id,
        target_id: packageId,
        type: 'IMPORTS',
        metadata: { 
          specifiers,
          importPath 
        }
      });
    } else {
      // For internal imports, store the path for relationship detection
      this.fileNode.metadata.internalImports = this.fileNode.metadata.internalImports || [];
      this.fileNode.metadata.internalImports.push({
        path: importPath,
        specifiers,
        line: node.startPosition.row + 1
      });
    }
  }
  
  private handleComponentMetadata(componentNode: Node, astNode: any): void {
    // Extract template reference for relationship building
    const templateUrl = this.extractDecoratorProperty(astNode, 'templateUrl');
    if (templateUrl) {
      componentNode.metadata.templateUrl = templateUrl;
    }
    
    const styleUrls = this.extractDecoratorProperty(astNode, 'styleUrls');
    if (styleUrls) {
      componentNode.metadata.styleUrls = styleUrls;
    }
    
    // For standalone components, track imports
    const imports = this.extractDecoratorProperty(astNode, 'imports');
    if (imports) {
      componentNode.metadata.standaloneImports = imports;
    }
  }
  
  private isExternalPackage(importPath: string): boolean {
    // External if doesn't start with './' or '../'
    return !importPath.startsWith('.') && !importPath.startsWith('/');
  }
  
  private getPackageName(importPath: string): string {
    // Handle scoped packages like @angular/core
    const parts = importPath.split('/');
    if (importPath.startsWith('@')) {
      return parts.slice(0, 2).join('/');
    }
    return parts[0];
  }
  
  private extractSnippet(node: any): string {
    // Extract first few lines for AI context
    const start = node.startIndex;
    const text = this.sourceCode.substring(start, start + 200);
    return text.split('\n').slice(0, 3).join('\n') + '...';
  }
}
```

## Simplified Relationship Detection (No LSP)

```typescript
class RelationshipDetector {
  async analyze(graph: Graph): Promise<Graph> {
    // 1. Resolve internal imports
    await this.resolveInternalImports(graph);
    
    // 2. Connect Angular templates to components
    await this.connectAngularTemplates(graph);
    
    // 3. Detect function calls within files
    await this.detectIntraFileCalls(graph);
    
    // 4. Handle Angular-specific relationships
    await this.detectAngularRelationships(graph);
    
    return graph;
  }
  
  private async resolveInternalImports(graph: Graph): Promise<void> {
    const files = graph.getNodesByType('FILE');
    
    for (const file of files) {
      const imports = file.metadata.internalImports || [];
      
      for (const imp of imports) {
        const resolvedPath = this.resolveImportPath(
          file.metadata.path,
          imp.path
        );
        
        const targetFile = this.findFileByPath(graph, resolvedPath);
        if (targetFile) {
          // Create import relationship
          graph.addEdge({
            source_id: file.id,
            target_id: targetFile.id,
            type: 'IMPORTS',
            metadata: {
              specifiers: imp.specifiers,
              line: imp.line
            }
          });
          
          // Try to resolve specific symbols
          for (const specifier of imp.specifiers) {
            const symbol = this.findSymbolInFile(graph, targetFile, specifier);
            if (symbol) {
              graph.addEdge({
                source_id: file.id,
                target_id: symbol.id,
                type: 'IMPORTS',
                metadata: { 
                  symbol: specifier 
                }
              });
            }
          }
        }
      }
    }
  }
  
  private async connectAngularTemplates(graph: Graph): Promise<void> {
    const components = [
      ...graph.getNodesByType('COMPONENT'),
      ...graph.getNodesByType('STANDALONE_COMPONENT')
    ];
    
    for (const component of components) {
      // Connect template file
      if (component.metadata.templateUrl) {
        const templatePath = this.resolveTemplatePath(
          component.metadata.path,
          component.metadata.templateUrl
        );
        
        const templateFile = this.findFileByPath(graph, templatePath);
        if (templateFile) {
          graph.addEdge({
            source_id: component.id,
            target_id: templateFile.id,
            type: 'USES_TEMPLATE',
            metadata: {}
          });
        }
      }
      
      // Connect style files
      if (component.metadata.styleUrls) {
        for (const styleUrl of component.metadata.styleUrls) {
          const stylePath = this.resolveTemplatePath(
            component.metadata.path,
            styleUrl
          );
          
          const styleFile = this.findFileByPath(graph, stylePath);
          if (styleFile) {
            graph.addEdge({
              source_id: component.id,
              target_id: styleFile.id,
              type: 'USES_STYLES',
              metadata: {}
            });
          }
        }
      }
    }
  }
  
  private resolveImportPath(fromFile: string, importPath: string): string {
    // Handle TypeScript path mappings and extensions
    const extensions = ['.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.js'];
    const basePath = path.resolve(path.dirname(fromFile), importPath);
    
    // Try each extension
    for (const ext of extensions) {
      const fullPath = basePath + ext;
      if (fs.existsSync(fullPath)) {
        return fullPath;
      }
    }
    
    // Try as directory with index file
    if (fs.existsSync(basePath) && fs.statSync(basePath).isDirectory()) {
      for (const indexFile of ['index.ts', 'index.js']) {
        const indexPath = path.join(basePath, indexFile);
        if (fs.existsSync(indexPath)) {
          return indexPath;
        }
      }
    }
    
    return basePath; // Return as-is, might not exist
  }
}
```

## Kuzu Database Export Format

```typescript
class KuzuExporter {
  constructor(private outputPath: string) {}
  
  async export(graph: Graph): Promise<void> {
    // Kuzu uses Cypher-like syntax
    const statements: string[] = [];
    
    // Create node tables
    statements.push(this.createNodeTableStatements());
    
    // Create edge tables
    statements.push(this.createEdgeTableStatements());
    
    // Insert nodes
    const nodesByType = this.groupNodesByType(graph);
    for (const [type, nodes] of nodesByType) {
      statements.push(...this.createNodeInsertStatements(type, nodes));
    }
    
    // Insert edges
    const edgesByType = this.groupEdgesByType(graph);
    for (const [type, edges] of edgesByType) {
      statements.push(...this.createEdgeInsertStatements(type, edges));
    }
    
    // Write to file
    const outputFile = path.join(this.outputPath, 'codebase_graph.cypher');
    await fs.writeFile(outputFile, statements.join('\n\n'));
    
    // Also export as JSON for AI consumption
    await this.exportJSON(graph);
  }
  
  private createNodeTableStatements(): string {
    return `
-- Node Tables
CREATE NODE TABLE IF NOT EXISTS File(
  id STRING PRIMARY KEY,
  name STRING,
  path STRING,
  extension STRING
);

CREATE NODE TABLE IF NOT EXISTS CodeEntity(
  id STRING PRIMARY KEY,
  type STRING,
  name STRING,
  path STRING,
  start_line INT64,
  end_line INT64,
  snippet STRING,
  decorators STRING[]
);

CREATE NODE TABLE IF NOT EXISTS ExternalPackage(
  id STRING PRIMARY KEY,
  name STRING
);
    `.trim();
  }
  
  private createEdgeTableStatements(): string {
    return `
-- Edge Tables
CREATE REL TABLE IF NOT EXISTS Contains(FROM File TO CodeEntity);
CREATE REL TABLE IF NOT EXISTS Defines(FROM CodeEntity TO CodeEntity);
CREATE REL TABLE IF NOT EXISTS Imports(FROM CodeEntity TO CodeEntity, specifiers STRING[]);
CREATE REL TABLE IF NOT EXISTS Calls(FROM CodeEntity TO CodeEntity);
CREATE REL TABLE IF NOT EXISTS UsesTemplate(FROM CodeEntity TO File);
CREATE REL TABLE IF NOT EXISTS UsesStyles(FROM CodeEntity TO File);
    `.trim();
  }
  
  private async exportJSON(graph: Graph): Promise<void> {
    // Simplified JSON format for AI consumption
    const aiFormat = {
      summary: {
        totalFiles: graph.getNodesByType('FILE').length,
        totalEntities: graph.getAllNodes().length - graph.getNodesByType('FILE').length,
        totalRelationships: graph.getAllEdges().length,
        entityTypes: this.countEntityTypes(graph),
        relationshipTypes: this.countRelationshipTypes(graph)
      },
      nodes: graph.getAllNodes().map(node => ({
        id: node.id,
        type: node.type,
        name: node.name,
        path: node.metadata.path,
        snippet: node.metadata.snippet
      })),
      edges: graph.getAllEdges().map(edge => ({
        source: edge.source_id,
        target: edge.target_id,
        type: edge.type
      }))
    };
    
    const jsonFile = path.join(this.outputPath, 'codebase_graph.json');
    await fs.writeFile(jsonFile, JSON.stringify(aiFormat, null, 2));
  }
}
```

## Monorepo Support

```typescript
class MonorepoDetector {
  static async detect(rootPath: string): Promise<MonorepoConfig | null> {
    // Check for Nx
    if (await fs.exists(path.join(rootPath, 'nx.json'))) {
      return this.detectNxWorkspaces(rootPath);
    }
    
    // Check for Lerna
    if (await fs.exists(path.join(rootPath, 'lerna.json'))) {
      return this.detectLernaPackages(rootPath);
    }
    
    // Check for Yarn workspaces
    const packageJson = await this.readPackageJson(rootPath);
    if (packageJson.workspaces) {
      return {
        type: 'yarn-workspaces',
        packages: await this.resolveWorkspacePatterns(
          rootPath,
          packageJson.workspaces
        )
      };
    }
    
    return null;
  }
  
  private static async detectNxWorkspaces(rootPath: string): Promise<MonorepoConfig> {
    const nxJson = JSON.parse(
      await fs.readFile(path.join(rootPath, 'nx.json'), 'utf-8')
    );
    
    const workspaceJson = await this.findWorkspaceConfig(rootPath);
    const projects = workspaceJson.projects || {};
    
    return {
      type: 'nx',
      packages: Object.entries(projects).map(([name, config]: [string, any]) => 
        typeof config === 'string' ? config : config.root
      )
    };
  }
}

// Integration in main flow
class CodeBasedCLI {
  async generateGraph(config: CodeBasedConfig): Promise<void> {
    // Auto-detect monorepo if not specified
    if (!config.monorepo) {
      const detected = await MonorepoDetector.detect(config.projectRoot);
      if (detected) {
        console.log(`🔍 Detected ${detected.type} monorepo structure`);
        config.monorepo = detected;
      }
    }
    
    if (config.monorepo) {
      // Process each package separately but in same graph
      for (const packagePath of config.monorepo.packages || []) {
        const fullPath = path.join(config.projectRoot, packagePath);
        console.log(`📦 Processing package: ${packagePath}`);
        
        // Process with package-specific context
        await this.processPackage(fullPath, config);
      }
      
      // Detect cross-package dependencies
      await this.detectCrossPackageDependencies(config);
    } else {
      // Standard single-project processing
      await this.processProject(config.projectRoot, config);
    }
  }
}
```

## CLI Command Structure

```typescript
// codebased/cli.ts
#!/usr/bin/env node

import { Command } from 'commander';
import { CodeBasedCLI } from './core';

const program = new Command();

program
  .name('codebased')
  .description('Generate knowledge graphs from your codebase')
  .version('1.0.0');

program
  .command('init')
  .description('Initialize CodeBased in your project')
  .action(async () => {
    // Create .codebased folder and config
    await initializeProject();
  });

program
  .command('analyze')
  .description('Analyze codebase and generate graph')
  .option('-t, --target <targets>', 'Target frameworks (angular,nodejs)', 'angular,nodejs')
  .option('-o, --output <path>', 'Output directory', '.codebased/graph')
  .action(async (options) => {
    const config: CodeBasedConfig = {
      projectRoot: process.cwd(),
      outputPath: options.output,
      targets: {
        angular: options.target.includes('angular'),
        nodejs: options.target.includes('nodejs')
      }
    };
    
    const cli = new CodeBasedCLI();
    await cli.generateGraph(config);
  });

program
  .command('update <files...>')
  .description('Update graph for specific files')
  .action(async (files, options) => {
    const cli = new CodeBasedCLI();
    await cli.updateGraph(config, files);
  });

program
  .command('query <cypher>')
  .description('Query the graph using Cypher syntax')
  .action(async (query) => {
    // Execute Kuzu query
    const results = await executeQuery(query);
    console.log(JSON.stringify(results, null, 2));
  });

program.parse();
```

## Example Output for AI Consumption

```json
{
  "summary": {
    "totalFiles": 156,
    "totalEntities": 892,
    "totalRelationships": 2341,
    "entityTypes": {
      "COMPONENT": 45,
      "SERVICE": 23,
      "MODULE": 12,
      "FUNCTION": 234,
      "CLASS": 89
    }
  },
  "criticalPaths": [
    {
      "type": "component_tree",
      "root": "AppComponent",
      "children": ["HeaderComponent", "MainComponent", "FooterComponent"]
    }
  ],
  "externalDependencies": [
    "@angular/core",
    "@angular/common",
    "rxjs",
    "lodash"
  ]
}
```

## Next Steps

1. **Start with Basic File Parsing**: Get the TypeScript/JavaScript parser working first
2. **Add Angular Detection**: Layer on Angular-specific entity detection
3. **Implement Relationship Detection**: Start with simple imports, then add more complex relationships
4. **Add Monorepo Support**: Detect and handle monorepo structures
5. **Optimize for AI**: Ensure output format is optimal for AI consumption

This MVP approach will give you a working tool quickly while leaving room for enhancement with LSP and deeper analysis later.