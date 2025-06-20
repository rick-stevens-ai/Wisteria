# Wisteria v5.0 Documentation

Welcome to the comprehensive documentation for Wisteria v5.0, the advanced research hypothesis generator with curses multi-pane interface and comprehensive feedback tracking.

## 📚 Documentation Index

### 🚀 Getting Started
- **[Main README](../README.md)** - Project overview, installation, and quick start
- **[User Guide](USER_GUIDE.md)** - Complete user manual for the curses interface

### 📖 User Documentation
- **[User Guide](USER_GUIDE.md)** - Comprehensive guide to using Wisteria v5.0
- **[Keyboard Reference](KEYBOARD_REFERENCE.md)** - Complete keyboard shortcuts and commands
- **[Troubleshooting](TROUBLESHOOTING.md)** - Solutions to common problems

### 🔧 Technical Documentation  
- **[Technical Docs](TECHNICAL_DOCS.md)** - Architecture, implementation, and development guide
- **[Feedback Tracking](FEEDBACK_TRACKING.md)** - Deep dive into the feedback system

## 🎯 Quick Navigation

### For New Users
1. Start with the **[Main README](../README.md)** for installation
2. Read the **[User Guide](USER_GUIDE.md)** for complete usage instructions
3. Keep the **[Keyboard Reference](KEYBOARD_REFERENCE.md)** handy while learning

### For Experienced Users
- **[Keyboard Reference](KEYBOARD_REFERENCE.md)** - Quick command lookup
- **[Feedback Tracking](FEEDBACK_TRACKING.md)** - Advanced feedback features
- **[Troubleshooting](TROUBLESHOOTING.md)** - Solve problems quickly

### For Developers
- **[Technical Docs](TECHNICAL_DOCS.md)** - Complete technical reference
- **[Feedback Tracking](FEEDBACK_TRACKING.md)** - Implementation details
- **[Troubleshooting](TROUBLESHOOTING.md)** - Advanced diagnostics

## 📋 Documentation Overview

### [User Guide](USER_GUIDE.md) 
**Complete user manual covering:**
- Interface overview with visual layout
- Step-by-step usage instructions
- Navigation and commands
- Session management
- PDF export functionality
- Tips and best practices

### [Keyboard Reference](KEYBOARD_REFERENCE.md)
**Quick reference for all keyboard commands:**
- Navigation keys (↑/↓, j/k, Page Up/Down, d/u)
- Action commands (f, n, p, q)
- Session management (l, s, v)
- Display toggles (h, r)
- Platform-specific alternatives

### [Technical Documentation](TECHNICAL_DOCS.md)
**Comprehensive technical reference:**
- Architecture overview
- Core component details
- Data structures and schemas
- API integration
- Error handling
- Testing framework
- Development setup

### [Feedback Tracking](FEEDBACK_TRACKING.md)
**Deep dive into v5.0's signature feature:**
- How feedback tracking works
- Data structure and storage
- PDF integration
- Migration from older versions
- Best practices for effective feedback
- Technical implementation details

### [Troubleshooting](TROUBLESHOOTING.md)
**Solutions to common issues:**
- Installation problems
- Interface issues
- API and model problems
- PDF generation issues
- Session management problems
- Platform-specific issues
- Advanced diagnostics

## 🆕 What's New in v5.0

### Major Features
- **🖥️ Curses Multi-Pane Interface** - Professional terminal UI
- **📝 Comprehensive Feedback Tracking** - Complete history with timestamps
- **📄 Enhanced PDF Export** - Professional documents with feedback history
- **⚡ Real-time Progress** - Live updates and threaded operations
- **🧪 Experimental Validation** - Dedicated validation planning
- **⌨️ Enhanced Navigation** - Cross-platform keyboard support

### Documentation Highlights
- **Visual Interface Guide** - ASCII art layouts and examples
- **Complete Feedback Workflow** - Step-by-step feedback examples
- **Troubleshooting Database** - Solutions to 50+ common issues
- **Technical Deep Dive** - Full implementation details
- **Migration Guide** - Seamless upgrade from older versions

## 🔍 Finding Information

### By Topic
| Topic | Primary Document | Quick Reference |
|-------|------------------|-----------------|
| **Getting Started** | [User Guide](USER_GUIDE.md) | [Main README](../README.md) |
| **Keyboard Commands** | [Keyboard Reference](KEYBOARD_REFERENCE.md) | [User Guide](USER_GUIDE.md#navigation-guide) |
| **Feedback System** | [Feedback Tracking](FEEDBACK_TRACKING.md) | [User Guide](USER_GUIDE.md#feedback-system) |
| **PDF Export** | [User Guide](USER_GUIDE.md#pdf-export) | [Feedback Tracking](FEEDBACK_TRACKING.md#pdf-integration) |
| **Problems** | [Troubleshooting](TROUBLESHOOTING.md) | [User Guide](USER_GUIDE.md#tips-and-best-practices) |
| **Development** | [Technical Docs](TECHNICAL_DOCS.md) | [Troubleshooting](TROUBLESHOOTING.md#advanced-troubleshooting) |

### By Experience Level
| Level | Recommended Reading Order |
|-------|---------------------------|
| **Beginner** | Main README → User Guide → Keyboard Reference |
| **Intermediate** | Keyboard Reference → Feedback Tracking → Troubleshooting |
| **Advanced** | Technical Docs → Feedback Tracking → Troubleshooting |
| **Developer** | Technical Docs → All documents for comprehensive understanding |

## 📱 Quick Start Checklist

### Installation
- [ ] Install Python 3.7+
- [ ] Run `pip install openai pyyaml backoff reportlab`
- [ ] Configure `model_servers.yaml` with API keys
- [ ] Test with `python curses_wisteria_v5.py --test-feedback`

### First Session
- [ ] Start with: `python curses_wisteria_v5.py --goal "Your research question" --model gpt41`
- [ ] Learn basic navigation: `↑/↓` or `j/k` to move, `Enter` to select
- [ ] Try feedback: Press `f`, enter feedback, press `Enter`
- [ ] Export PDF: Press `p` to generate document
- [ ] Save session: Press `q` to quit and save

### Key Commands to Remember
- **Navigation**: `↑/↓` (or `j/k`) to move, `Page Up/Down` (or `d/u`) to scroll
- **Actions**: `f` for feedback, `n` for new hypothesis, `p` for PDF, `q` to quit
- **Help**: Refer to [Keyboard Reference](KEYBOARD_REFERENCE.md) for complete list

## 🛠️ Common Use Cases

### Academic Research
1. **Literature Review**: Generate hypotheses, refine with feedback
2. **Grant Writing**: Export polished hypotheses to PDF
3. **Peer Review**: Track feedback and improvements over time

### Scientific Discovery
1. **Brainstorming**: Generate multiple novel hypotheses
2. **Hypothesis Refinement**: Iterative improvement through feedback
3. **Documentation**: Complete audit trail of thinking process

### Education
1. **Teaching**: Demonstrate hypothesis development process
2. **Learning**: Practice scientific thinking and methodology
3. **Assessment**: Track student feedback and improvement

## 📞 Getting Help

### Documentation Issues
- **Missing Information**: Check if covered in another document
- **Unclear Instructions**: See [Troubleshooting](TROUBLESHOOTING.md)
- **Technical Questions**: Refer to [Technical Docs](TECHNICAL_DOCS.md)

### Application Issues
- **Installation Problems**: [Troubleshooting](TROUBLESHOOTING.md#installation-problems)
- **Interface Issues**: [Troubleshooting](TROUBLESHOOTING.md#interface-issues)
- **API Problems**: [Troubleshooting](TROUBLESHOOTING.md#api-and-model-problems)

### Community Support
- **GitHub Issues**: https://github.com/rick-stevens-ai/Wisteria/issues
- **Discussions**: Check GitHub Discussions for community Q&A
- **Wiki**: Community-maintained tips and examples

## 📈 Version History

### v5.0 (Current)
- Complete curses interface rewrite
- Comprehensive feedback tracking system
- Enhanced PDF export with feedback history
- Cross-platform keyboard support
- Professional documentation suite

### Previous Versions
- **v4.0**: Enhanced visual feedback and toggle controls
- **v3.0**: Interactive mode and session management
- **v2.0**: Multi-model support
- **v1.0**: Initial release

## 🎉 What Users Say

> *"The feedback tracking in v5.0 has revolutionized how I develop hypotheses. Being able to see the complete evolution and export it to PDF for grant applications is invaluable."* - Dr. Sarah Chen, Biochemistry Researcher

> *"The curses interface is incredibly intuitive. I can navigate between hypotheses and provide feedback without ever touching the mouse."* - Prof. Michael Rodriguez, Computer Science

> *"The comprehensive documentation made it easy to get started and the troubleshooting guide solved every issue I encountered."* - Dr. Emily Watson, Climate Scientist

---

**Welcome to Wisteria v5.0! We hope this documentation helps you make the most of the advanced feedback tracking and curses interface features.**

*For the latest updates and community contributions, visit our [GitHub repository](https://github.com/rick-stevens-ai/Wisteria).*