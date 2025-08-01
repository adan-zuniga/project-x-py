# GitHub Issue #12 Metadata

**Title**: Async/Await Refactoring Plan for project-x-py  
**Number**: 12  
**State**: Open  
**URL**: https://github.com/TexasCoding/project-x-py/issues/12  
**Created**: 2025-07-30T22:46:46Z  
**Updated**: 2025-07-30T22:48:42Z  
**Author**: TexasCoding  
**Assignee**: TexasCoding  

## Description
This issue contains a comprehensive plan to refactor the project-x-py SDK from synchronous to asynchronous operations. The main content has been saved to `async_refactoring_issue.md`.

## Key Points
- Complete migration from sync to async architecture
- No backward compatibility (per CLAUDE.md directives)
- 5-6 week implementation timeline
- Uses httpx for async HTTP and needs async SignalR solution
- All public APIs will become async methods